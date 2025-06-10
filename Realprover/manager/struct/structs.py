import dataclasses
import types
import typing
from functools import cached_property
from dataclasses import dataclass, field
from typing import Optional
from operator import attrgetter

Name = list[str | int]
ImportInfoRaw = list[Name]

@dataclass
class StringRange:
    """Byte position within a file"""
    start: int
    stop: int

    def as_slice(self) -> slice:
        return slice(self.start, self.stop)

@dataclass
class Param:
    bi: str
    type: Optional[StringRange]


@dataclass
class Modifiers:
    visibility: str
    is_noncomputable: bool
    rec_kind: str
    is_unsafe: bool
    doc_string: Optional[str] = field(default=None)


@dataclass
class Syntax:
    original: bool
    range: Optional[StringRange]


@dataclass
class DeclarationInfoRaw:
    kind: str
    id: Optional[Syntax]
    name: Name
    fullname: Name
    modifiers: Modifiers
    params: Optional[list[Param]]
    type: Optional[Syntax]
    value: Optional[Syntax]
    tactics: list[Syntax]
    ref: Optional[Syntax]


@dataclass
class SymbolInfoRaw:
    name: Name
    type: Optional[str]
    kind: str
    typeReferences: Optional[list[Name]]
    valueReferences: Optional[list[Name]]
    isProp: bool


@dataclass
class Module:
    pass


@dataclass
class Variable:
    name: Name
    type: str
    is_prop: bool
    binder_info: str = field(default="default")
    value: Optional[str] = field(default=None)

    @cached_property
    def pretty(self) -> str:
        s = f"{pretty_name(self.name)} : {self.type}"
        if self.value is not None:
            s += " := " + self.value
        return s

    @cached_property
    def as_param(self) -> str:
        if self.value is not None:
            raise ValueError("Let-bindings should not be used as parameters")
        if self.binder_info == "instImplicit":
            return f"[{self.type}]"
        if self.binder_info == "default":
            l, r = "(", ")"
        elif self.binder_info == "implicit":
            l, r = "{", "}"
        elif self.binder_info == "strictImplicit":
            l, r = "{{", "}}"
        else:
            raise RuntimeError("Unexpected binder_info")
        return f"{l}{self.pretty}{r}"


@dataclass
class Goal:
    context: list[Variable]
    type: str
    is_prop: bool

    @cached_property
    def pretty(self) -> str:
        return "\n".join(v.pretty for v in self.context) + "\n⊢ " + self.type

    @cached_property
    def as_signature(self) -> str:
        return " ".join(v.as_param for v in self.context if v.value is None) + " : " + self.type

def state_repr(state: Goal | list[Goal]) -> str:
    if not state:
        return "no goals"
    if isinstance(state, Goal):
        return state.pretty
    if isinstance(state, list):
        if len(state) == 1:
            return state[0].pretty
        state_str = f"case:\n{state[0].pretty}"
        for i in state[1:]:
            state_str += f"\n\ncase:\n{i.pretty}"
        return state_str
    raise TypeError


def state_repr_dedup(state: list[Goal]) -> str:
    k = []
    for goal in state:
        prop = [v for v in goal.context if v.is_prop]
        prop.sort(key=attrgetter("type"))
        dedup_prop = []
        for p in prop:
            if not dedup_prop or dedup_prop[-1].type != p.type:
                dedup_prop.append(p)
        non_prop = [v for v in goal.context if not v.is_prop]
        k.append("\n".join(v.pretty for v in dedup_prop + non_prop) + "\n⊢ " + goal.type)
    k = "\n\n".join(k)
    # print(k)
    # import ipdb;ipdb.set_trace()
    return k

@dataclass
class ProofVariable:
    name: str
    type: str


@dataclass
class ProofGoal:
    context: list[ProofVariable]
    type: str


@dataclass
class TacticInfo:
    kind: Name
    original: bool
    range: Optional[StringRange] = field(default=None)


@dataclass
class TacticElabInfo:
    tactic: TacticInfo
    references: Optional[list[Name]]
    before: list[Goal]
    after: list[Goal]


# TODO: add «» quoting when necessary
def pretty_name(name: Name):
    return ".".join(str(c) for c in name)


# TODO: use pydantic
def snake_to_camel(s: str) -> str:
    words = s.split("_")
    return words[0] + "".join(w.capitalize() for w in words[1:])


def extract_field(data: dict, f: dataclasses.Field):
    k = snake_to_camel(f.name)
    if f.default is not dataclasses.MISSING:
        return data.get(k, f.default)
    elif f.default_factory is not dataclasses.MISSING:
        return data.get(k, f.default_factory())
    else:
        return data[k]

@dataclass
class Node:
    sid: int
    parent_sid: int
    tactic: str
    state: list[Goal]
    depth: int = 0
    score: float = 0
    parent: Optional["Node"] = None
    
    @property
    def current_path(self):
        path = []
        current = self
        while current:
            path.append(current)
            current = current.parent
        path.reverse()  # Reverse the path to get it from root to current node
        return path

def from_json(tp: type, data):
    origin = typing.get_origin(tp)
    if origin is typing.Union or origin is types.UnionType:
        args = typing.get_args(tp)
        for arg in args:
            try:
                return from_json(arg, data)
            except:
                pass
        raise TypeError(f"union {tp}")
    elif origin is list:
        (arg,) = typing.get_args(tp)
        # print(data)
        if not isinstance(data, list):
            raise TypeError(f"list {tp}")
        return [from_json(arg, x) for x in data]
    elif origin is dict:
        (kt, vt) = typing.get_args(tp)
        if not isinstance(data, dict):
            raise TypeError(f"dict {tp}")
        assert kt is str
        return {k: from_json(vt, v) for k, v in data.items()}
    elif tp is StringRange:
        if not isinstance(data, list):
            raise TypeError(f"list {tp}")
        return StringRange(start=data[0], stop=data[1])
    elif dataclasses.is_dataclass(tp):
        tp: dataclass
        fields = dataclasses.fields(tp)
        return tp(**{f.name: from_json(f.type, extract_field(data, f)) for f in fields})
    else:
        if not isinstance(data, tp):
            # print(data, tp)
            raise TypeError(tp)
        return data