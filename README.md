[![Documentation Status](https://readthedocs.org/projects/desdeo-restful/badge/?version=latest)](https://desdeo-restful.readthedocs.io/en/latest/?badge=latest)

# desdeo-webapi

Table of contents:
- [desdeo-webapi](#desdeo-webapi)
  - [Installation](#installation)
  - [Usage](#usage)
    - [Authentication](#authentication)
    - [Basic usage](#basic-usage)
    - [Tests](#tests)
  - [Documentation](#documentation)
  - [Assumptions](#assumptions)
  - [Features](#features)
    - [Implemented](#implemented)

`desdeo-webapi` is a web API (application programming interface) that exposes parts of the
[DESDEO framework](https://desdeo.it.jyu.fi/)
to be used in web applications
to build software for interactive multiobjective optimization. `desdeo-webapi` is mainly based on `flask`, `flask-restx`,
and [desdeo](https://github.com/industrial-optimization-group/DESDEO).
To use the API, authentication is required, which is handled using JWT access and refresh tokens. This means that
at least one user should be added (registered) to the database so that the API may be used.

## Installation

After cloning and switching to the directory with the repository's contents, it
is recommended to install `desdeo-webapi` utilizing
[poetry](https://python-poetry.org/):

```
$> git clone git@github.com:gialmisi/desdeo-webapi.git
$> cd desdeo-webapi
$> poetry install
```
It is recommended to use virtual environemnts. If `poetry` was used to install the project
as described above, one can switch to the virtual environment spawned by poetry by running the
command:

```
$> poetry shell
```

## Usage

These instructions are for running a local server, which implements the API defined in `desdeo-webapi`.
In this section, it is assumed that `desdeo-webapi` has been succesfully installed using poetry. The commands
shown should be run in the root directory of `desdeo-webapi` and in the virtual environment with the
installed dependencies.

### Authentication

To use the API implemented in `desdeo-webapi`, a user should be registered to
the database for authentication.  For experimenting with the API locally, there
is the script `add_exp_users.py` which can be executed to create a new database with a number of users each with
a multiobjective optimization problem defined for them. To add a single user, run the command:

```
$> python add_exp_users.py --username user --N 1
```

This will add a new user with the username `user1` with a randomly generated password to the database. The password
will be printed to the standard output after running the above command. More users may be added by incrementing the
number after `--N`, and the username prefix can be changed by changing the argument of `--username`. The users added
alongside their passwords will be also stored in a CSV file named 'users_and_pass.csv`.

### Basic usage

To run a local server, simply run the command:

```
$> python run.py
```

This will launch a local server on an address which will be printed to the standard output. For example
`http://127.0.0.1:5000/`, but this may vary based on the system `desdeo-webapi` is run on.

### Tests

There are a bunch of tests which may be run to check the proper functioning of `desdeo-webapi`. First, development
dependencies must be installed by running the command:

```
$> poetry install --development
```

After the development dependencies have been successfully installed, `pytest` can be used to execute all the tests
by running the command

```
$> pytest
```

Executing all the tests will take some time. Some tags have been defined in the file `pytest.ini`, which may be used
to run particular subsets of tests.

## Documentation

The documentation of API implemented in `desdeo-webapi` is available on [readthedocs](https://desdeo-restful.readthedocs.io/en/latest/?badge=latest).

## Assumptions

This is a list of assumptions that hold throughout `desdeo-webapi`. They should be kept in mind when using the library.

- Everything passed from an to the API defined in `desdeo-webapi` is assumed to
  be minimized. In some places, like when defining a multiobjective optimization
  problem with an analytical formulation, information is stored whether some
  objectives are to be minimized or maximized (i.e., the JSON field `minimized`).
  This information is purely informative and is not made use of in any of the
  internal computation that result. **Everything should be supplied through the
  API in a form which is to be minimized!**

## Features

### Implemented

- Registering new users, logging in, logging out, JWT token authorization.
- Defining multiobjective optimization problems with analytical formulations.
- Solving multiobjective optimization problems with analytical and discrete formulations using the following interactive methods:
  - Synchronous NIMBUS
  - The reference point method
  - NAUTILUS Navigator
  - RVEA
  - E-NAUTILUS
