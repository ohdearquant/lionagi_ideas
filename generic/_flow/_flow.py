"""flow as categorical sequences"""

from collections.abc import Mapping
from collections import deque
from typing import Tuple
from pydantic import Field
import contextlib
from ..abc import Record, Component, LionTypeError, ItemNotFoundError, LionIDable
from .._pile._pile import Pile, pile

from ._progression import Progression, progression


class Flow(Component):

    sequences: Pile[Progression] = Field(default_factory=lambda: pile({}, Progression))
    registry: dict[str, str] = {}
    default_name: str = "main"
    

    def all_orders(self) -> list[list[str]]:
        return [list(seq) for seq in self.sequences]
    
    def all_unique_items(self) -> Tuple[str]:
        return tuple({item for seq in self.sequences for item in seq})
    
    def keys(self):
        yield from self.sequences.keys()
    
    def values(self):
        yield from self.sequences.values()
    
    def items(self):
        yield from self.sequences.items()
        
    def get(self, seq=None, index=None, default=...):
        # if index is None, we return the branch
        with contextlib.suppress(ItemNotFoundError):
            seq = self._find_branch(seq, None)
            seq = self.registry[seq] if seq in self.registry else seq
            seq = self.sequences[seq]
            
            if index and isinstance(index, (int, slice)):
                return seq[index]
            return seq
        
        if default == ...:
            raise ItemNotFoundError("Branch not found.")
        return default  
        
    def __getitem__(self, seq=None, index=None, /):
        return self.get(seq, index)
        
    def __setitem__(self, seq: LionIDable | str, index=None, value=None, /):
        if seq not in self:
            raise ItemNotFoundError(f"Branch {seq}")
        
        if index and isinstance(index, (int, slice)):
            self.sequences[seq][index] = value
            return
        
        self.sequences[seq] = value

    def __contains__(self, item):
        return (
            item in self.registry or
            item in self.sequences or
            item in self.all_unique_items()
        )
        
    def shape(self):
        return (len(self.all_orders()), [len(i) for i in self.all_orders()])
    
    def size(self):
        return sum(len(seq) for seq in self.all_orders())
    
    def clear(self):
        self.sequences.clear()
        self.registry.clear()

    def include(self, seq=None, item=None, name=None):
        _branch = self._find_branch(seq, None) or self._find_branch(name, None)
        if not _branch:
            if not item and not name:
                """None is not in the registry or branches."""
                return False
            if item:
                self.append(item, name)
                return item in self
            
        else:
            if _branch in self:
                if not item and not name:
                    return True
                if item:
                    self.append(item, _branch)
                    return item in self
                return True # will ignore name if branch is already found
            
            else:
                if isinstance(seq, Progression):
                    if item and seq.include(item):
                        self.register(seq, name)
                    return seq in self
                
                return False

    def exclude(self, seq: LionIDable=None, item=None, name=None):
        
        # if branch is not None, we will not check the name
        if seq is not None:
        
            with contextlib.suppress(ItemNotFoundError):
                if item:
                    # if there is item, we exclude it from the branch
                    return self.sequences[seq].exclude(item)
                else:
                    # if there is no item, we exclude the branch
                    a = self.registry.pop(seq.name or seq.ln_id, None)
                    return a is not None and self.sequences.exclude(seq)
            return False
        
        
        elif name is not None:
            
            with contextlib.suppress(ItemNotFoundError):
                if item:
                    # if there is item, we exclude it from the branch
                    return self.sequences[self.registry[name]].exclude(item)
                else:
                    # if there is no item, we exclude the branch
                    a = self.registry.pop(name, None)
                    return a is not None and self.sequences.exclude(a)
            return False
        
    def register(self, branch: Progression, name: str = None):
        if not isinstance(branch, Progression):
            raise LionTypeError(f"Branch must be of type Progression.")
        if (name := branch.name or name) is None:
            if self.default_name in self.registry:
                name = branch.ln_id
            else:
                name = self.default_name
        if name in self.registry:
            raise ValueError(f"Branch '{name}' already exists.")
        self.sequences.include(branch)
        self.registry[name] = branch.ln_id

    def append(self, item, branch=None, /):
        if not branch:
            if self.default_name in self.registry:
                branch = self.registry[self.default_name]
                self.sequences[branch].include(item)
                return
            
            p = progression(item, self.default_name)
            self.register(p)
            return
                
        if branch in self.sequences:
            self.sequences[branch] += item
            return
        
        if branch in self.registry:
            self.sequences[self.registry[branch]] += item
            return 
        
        p = progression(item, branch if isinstance(branch, str) else None)
        self.register(p)
        
    def popleft(self, branch=None, /):
        branch = self._find_branch(branch)
        return self.sequences[branch].popleft()

    def shape(self):
        return {branch: len(seq) for branch, seq in self.items()}

    def get(self, branch: str, /, default=False) -> deque[str] | None:
        try:
            return self.sequences[branch]
        except KeyError as e:
            if default == False:
                raise e
            return default

    def remove(self, item, branch="all"):
        """if branch is 'all', will attempt to remove the item from all branches."""
        if branch == "all":
            for seq in self.sequences:
                seq.remove(item)
                   
        branch = self._find_branch(branch)
        self.sequences[branch].remove(item)

    def __len__(self):
        return len(self.sequences)

    def __iter__(self):
        return iter(self.sequences)

    def __next__(self):
        return next(self.__iter__())

    def _find_branch(self, branch=None, default=...):
        """find the branch id in the registry or branches. can be name, progression obj or id"""
        
        if not branch:
            if self.default_name in self.registry:
                return self.registry[self.default_name]
            if default != ...:
                return default
            raise ItemNotFoundError("No branch found.")
                
        if branch in self.sequences:
            return branch.ln_id if isinstance(branch, Progression) else branch
        
        if branch in self.registry:
            return self.registry[branch]


def flow(sequences=None, /):
    if sequences is None:
        return Flow()
    
    flow = Flow()
    
    # if mapping we assume a dictionary of in {name: data} format
    if isinstance(sequences, (Mapping, Record)):
        for name, seq in sequences.items():
            if not isinstance(seq, Progression):
                try:
                    seq = progression(seq, name)
                except Exception as e:
                    raise e
            flow.register(seq)
        return flow
    
    for seq in sequences:
        if not isinstance(seq, Progression):
            try:
                seq = progression(seq)
            except Exception as e:
                raise e
        flow.register(seq)
    return flow
