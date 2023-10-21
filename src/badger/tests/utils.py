import pandas as pd
from xopt import VOCS
from xopt.generators import RandomGenerator, UpperConfidenceBoundGenerator


def create_routine():
    from badger.routine import Routine

    test_routine = {
        "name": "routine-for-core-test",
        "algo": "random",
        "env": "test",
        "algo_params": {},
        "env_params": {},
        "config": {
            "variables": {
                "x0": [-1, 1],
                "x1": [-1, 1],
                "x2": [-1, 1],
                "x3": [-1, 1]
            },
            "objectives": {"f": "MAXIMIZE"},
            "init_points": {"x0": [0.5], "x1": [0.5], "x2": [0.5], "x3": [0.5]},
        },
    }

    vocs = VOCS(
        variables=test_routine["config"]["variables"],
        objectives=test_routine["config"]["objectives"],
    )

    generator = RandomGenerator(vocs=vocs)

    return Routine(
        name="test",
        vocs=vocs,
        generator=generator,
        environment={"name": "test"},
        initial_points=pd.DataFrame(test_routine["config"]["init_points"])
    )


def create_routine_turbo():
    from badger.routine import Routine

    test_routine = {
        "name": "routine-for-turbo-test",
        "algo": "upper_confidence_bound",
        "env": "test",
        "algo_params": {
            "turbo_controller": "optimize",
            "gp_constructor": {
                "name": "standard",
                "use_low_noise_prior": True,
            },
            "beta": 2.0,
        },
        "env_params": {},
        "config": {
            "variables": {
                "x0": [-1, 1],
                "x1": [-1, 1],
                "x2": [-1, 1],
                "x3": [-1, 1]
            },
            "objectives": {"f": "MAXIMIZE"},
            "init_points": {"x0": [0.5], "x1": [0.5], "x2": [0.5], "x3": [0.5]},
        },
    }

    vocs = VOCS(
        variables=test_routine["config"]["variables"],
        objectives=test_routine["config"]["objectives"],
    )

    generator = UpperConfidenceBoundGenerator(
        vocs=vocs, ** test_routine["algo_params"])

    return Routine(
        name="test-turbo",
        vocs=vocs,
        generator=generator,
        environment={"name": "test"},
        initial_points=pd.DataFrame(test_routine["config"]["init_points"])
    )
