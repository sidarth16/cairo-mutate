from .as_flip import mutate_as_flip
from .as_rem import mutate_as_rem
from .op_ari import mutate_op_ari
from .op_asg import mutate_op_asg
from .op_eq import mutate_op_eq

MUTATOR_REGISTRY = {
    "as_rem": {
        "name": "as_rem",
        "label": "AS-REM",
        "description": "Assert Removal",
        "fn": mutate_as_rem,
    },
    "as_flip": {
        "name": "as_flip",
        "label": "AS-FLIP",
        "description": "Assert Condition Flip",
        "fn": mutate_as_flip,
    },
    "op_eq": {
        "name": "op_eq",
        "label": "OP-EQ",
        "description": "Equality Operator Mutation",
        "fn": mutate_op_eq,
    },
    "op_ari": {
        "name": "op_ari",
        "label": "OP-ARI",
        "description": "Arithmetic Operator Mutation",
        "fn": mutate_op_ari,
    },
    "op_asg": {
        "name": "op_asg",
        "label": "OP-ASG",
        "description": "Assignment Operator Mutation",
        "fn": mutate_op_asg,
    },
}

DEFAULT_MUTATORS = list(MUTATOR_REGISTRY.keys())
