import pickle
import torch
from typing import List, Dict, Union
from torch import Tensor
from transformers import BartTokenizer
from psp.constants import (
    OntologyVocabs,
    DatasetPaths,
    EOSPAN_TOKEN,
)


class Tokenizer:
    """] is the special token to indicate the enclosure of a span (either by intent or slot)"""

    def __init__(self, pretrained: str, dataset_path: DatasetPaths):
        # Init tokenizer and add ontology vocabs
        self.tokenizer: BartTokenizer = BartTokenizer.from_pretrained(pretrained)
        # Read onotlogy vocabs
        if dataset_path == DatasetPaths.TOPv2:
            self._read_topv2_ontology_vocabs()
        else:
            raise ValueError("{} is an unsupported dataset.".format(dataset_path))

    def batch_encode_plus(self, batch_text: List[str], **kwargs):
        return self.tokenizer.batch_encode_plus(batch_text, **kwargs)

    def _read_topv2_ontology_vocabs(self):
        """Read TOPv2 ontology vocabs and add to tokenizer."""
        # Read ontology vocab
        with open(OntologyVocabs.TOPv2.value, "rb") as file:
            self.ontology_per_domain_map: Dict[str, Dict[str, List[str]]] = pickle.load(
                file
            )
        # Get lists of intents and slots
        self.intent_list: List[str] = []
        self.slot_list: List[str] = []
        for ontology_per_domain in self.ontology_per_domain_map.values():
            self.intent_list.extend(ontology_per_domain["intents"])
            self.slot_list.extend(ontology_per_domain["slots"])

        # Remove duplicates (if existed)
        self.intent_list = list(set(self.intent_list))
        self.slot_list = list(set(self.slot_list))

        # Add ontology vocabs to tokenizer
        # ] is the special token indicating the enclousre of a span
        ontology_list: List[str] = list(
            set(self.intent_list + self.slot_list + [EOSPAN_TOKEN])
        )

        new_added_ontology_token_num: int = self.tokenizer.add_tokens(
            ontology_list, special_tokens=True
        )
        print("Added {} ontology tokens.".format(new_added_ontology_token_num))

        # get ids of ontology vocab
        self.ontology_id_list: List[int] = self.tokenizer.encode(ontology_list)[1:-1]
        ontology_to_id_map: Dict[str, int] = {
            key: value for key, value in zip(ontology_list, self.ontology_id_list)
        }

        # token_id of EOSPAN_TOKEN
        self.eospan_token_id: int = ontology_to_id_map[EOSPAN_TOKEN]

        # create mappings: ontology -> ids and ids -> ontology
        self.intent_to_id_map: Dict[str, int] = {}
        self.id_to_intent_map: Dict[int, str] = {}

        for key in self.intent_list:
            value = ontology_to_id_map[key]
            self.intent_to_id_map[key] = value
            self.id_to_intent_map[value] = key

        self.slot_to_id_map: Dict[str, int] = {}
        self.id_to_slot_map: Dict[int, str] = {}
        for key in self.slot_list:
            value = ontology_to_id_map[key]
            self.slot_to_id_map[key] = value
            self.id_to_slot_map[value] = key

        # Save tensors of intents and slots
        self.intent_tensors: Tensor = torch.tensor(list(self.intent_to_id_map.values()))
        self.slot_tensors: Tensor = torch.tensor(list(self.slot_to_id_map.values()))

    def __call__(
        self, inputs: Union[str, List[str]], **kwargs
    ) -> Union[List[int], List[List[int]]]:
        return self.tokenizer(inputs, **kwargs)

    """
    @property
    def bos_token_id(self) -> int:
        return self.tokenizer.bos_token_id

    @property
    def bos_token(self) -> str:
        return self.tokenizer.bos_token
    
    @property
    def eos_token(self) -> str:
        return self.tokenizer.eos_token

    @property
    def eos_token_id(self) -> int:
        return self.tokenizer.eos_token_id
    
    @property
    def pad_token(self) -> str:
        return self.tokenizer.pad_token
    
    @property
    def pad_token_id(self) -> int:
        return self.tokenizer.pad_token_id
    """
    
    def decode(self, *args, **kwargs):
        return self.tokenizer.decode(*args, **kwargs)

    @property
    def max_seq_len(self) -> int:
        return self.tokenizer.model_max_length

    @property
    def bos_token_id(self) -> int:
        return self.tokenizer.bos_token_id

    @property
    def eos_token_id(self) -> int:
        return self.tokenizer.eos_token_id

    @property
    def pad_token_id(self) -> int:
        return self.tokenizer.pad_token_id

    @property
    def vocab(self) -> Dict[str, int]:
        return self.tokenizer.get_vocab()

    @property
    def vocab_size(self) -> int:
        return len(self.tokenizer)

    @property
    def ontology_vocab_ids(self) -> int:
        return self.ontology_id_list

    @property
    def ontology_vocab_size(self) -> int:
        return len(self.ontology_list)

    @property
    def num_intent(self) -> int:
        return len(self.intent_list)

    @property
    def num_slot(self) -> int:
        return len(self.slot_list)

    @property
    def map_id_to_intent(self, id: int) -> str:
        return self.id_to_intent_map[id]

    @property
    def map_id_to_slot(self, id: int) -> str:
        return self.id_to_slot_map[id]

    @property
    def map_intent_to_id(self, key: str) -> int:
        return self.map_intent_to_id[key]

    @property
    def map_slot_to_id(self, key: str) -> int:
        return self.map_slot_to_id[key]

    @property
    def end_of_span_token(self):
        return EOSPAN_TOKEN

    @property
    def end_of_span_token_id(self):
        return self.eospan_token_id

    @property
    def intent_id_list(self) -> List[int]:
        return list(self.intent_to_id_map.values())

    @property
    def slot_id_list(self) -> List[int]:
        return list(self.slot_to_id_map.values())

    def save_pretrained(self, *args, **kwargs) -> None:
        self.tokenizer.save_pretrained(*args, **kwargs)


class PointerTokenizer(Tokenizer):
    """Reset indices of ontology-tokens to 0-index"""
    def __init__(self, pretrained: str, dataset_path: DatasetPaths):
        super(PointerTokenizer, self).__init__(pretrained=pretrained, dataset_path=dataset_path)

        # add special pointer vocabs
        self._add_special_pointer_vocabs()

    def _add_special_pointer_vocabs(self) -> None:
        """Add the set of special pointer vocabs of MODEL_MAX_LEN pointers"""
        # Generate set of special pointers
        # Each pointer is formulated as @ptr# that # is the index
        pointer_set = ["@ptr{}".format(x) for x in range(self.tokenizer.model_max_length)]

        # Add pointer tokens to tokenizer
        new_added_pointer_token_num: int = self.tokenizer.add_tokens(
            pointer_set, special_tokens=True
        )
        print("Added {} poitner tokens.".format(new_added_pointer_token_num))

        # Get token-id map of pointers
        pointer_id_list: List[int] = self.tokenizer.encode(pointer_set)[1:-1]
        self.pointer_to_id_map: Dict[str, int] = {}
        self.id_to_pointer_map: Dict[int, str] = {}

        for ptr, id in zip(pointer_set, pointer_id_list):
            self.pointer_to_id_map[ptr] = id
            self.id_to_pointer_map[id] = ptr

        # declare pointer-transform (for classification)
        self.pointers_to_vocabs: Tensor = torch.tensor(pointer_id_list + self.ontology_id_list + [self.eos_token_id, self.bos_token_id, self.pad_token_id, self.tokenizer.unk_token_id])
        
        self.vocabs_to_pointers: Tensor = torch.full((self.vocab_size,), fill_value=-1)
        self.vocabs_to_pointers[self.pointers_to_vocabs] = torch.arange(len(self.pointers_to_vocabs))

    def map_pointer_to_id(self, ptr: str) -> int:
        return self.pointer_to_id_map[ptr]

    def map_id_to_poitner(self, id: int) -> str:
        return self.id_to_pointer_map[id]
    
    @property
    def pointer_list(self) -> List[str]:
        return list(self.pointer_to_id_map.keys())

    @property
    def pointer_set_size(self) -> int:
        return len(self.pointer_to_id_map)

    @property
    def output_vocab_size(self) -> int:
        # 4 to compensate for special tokens: <BOS>, <PAD>, <UNK>, and <EOS>
        return self.ontology_vocab_size + self.pointer_set_size + 4

    def transform(self, inputs: Tensor) -> Tensor:
        return self.vocabs_to_pointers[inputs]

    def reverse_transform(self, inputs: Tensor) -> Tensor:
        return self.pointers_to_vocabs[inputs]

    def batch_encode_vocabs_to_pointers(self, sequences: List[str], **kwargs):
        pointer_parse = super().batch_encode_plus(sequences, **kwargs, return_tensor="pt")
        pointer_parse["input_ids"] = self.transform(pointer_parse["input_ids"])

        return pointer_parse

    def batch_decode_pointers_to_vocabs(self, inputs: Tensor) -> Tensor:
        return self.reverse_transform(inputs)
