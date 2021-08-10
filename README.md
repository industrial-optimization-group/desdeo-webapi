# desdeo-restful

`desdeo-restful` is a (restful) web API that exposes parts of the DESDEO framework to be used in web applications
to build software for interactive multiobjective optimization. `desdeo-restful` is mainly based on `flask` and `flask-restx`.
To use the API, authentication is required, which is currently handled using JWT access and refresh tokens. This means that
at least one user should be added (registered) to the database.

## Installation

TODO

## Usage

### Authentication

As mentioned, to use the API implemented in `desdeo-restful`, a user should be registered to the database for authentication.
For experimenting
with the API locally, there is (TODO!!!) some script that can be executed to create a new database with a specified username and
password, and to also add a couple of readily defined multiobjective optimization problems to experiment with.

### Basic usage

TODO

## Documentation

The documentation of API implemented in `desdeo-restful` is available on readthedocs. The documentation is not complete. (TODO)

## Assumptions

This is a list of assumptions that hold throughout `desdeo-restful`. They should be kept in mind when using the library.

- Everything passed from an to the API defined in `desdeo-restful` is assumed to be minimized. In some places, like when defining
  a multiobjective optimization problem with an analytical formulation, information is stored whether some objectives are to be
  minimized or maximized (i.e., the JSON field `minimized`). This information is purely informative and is not made use of in
  any of the internal computation that result. **Everything should be supplied through the API in a form which is to be minimized!**

## Features

### Implemented

- Registering new users, logging in, logging out, JWT token authorization.
- Defining multiobjective optimization problems with analytical formulations.
- Solving multiobjective optimization problems with analytical and discrete formulations using the following interactive methods:
  - Synchronous NIMBUS
  - The reference point method

### WIP

- Defining multiobjective optimization problems with discrete formulations.
- Solving multiobjective optimization problems with discrete formulation using the following interactive methods:
  - NAUTILUS Navigator
