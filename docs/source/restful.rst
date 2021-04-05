HTTP endpoints
==============

.. toctree
    :maxdepth: 2
    :caption: Contents

Login and Registration
----------------------

.. http:post:: /login

    Login and authenticate with existing user credentials.

    **Example request**:

    .. sourcecode:: http

      POST /login HTTP/1.1
      Host: example.com
      Accept: application/json

      {
        "username": "user",
        "password": "pass"
      }

    **Example response**:

    .. sourcecode:: http

      HTTP/1.1 200 OK
      Vary: Accept
      Content-Type: application/json

      {
        "message": "Logged as user",
        "access_token": "access_token",
        "refresh_token": "refresh_token"
      }

    :<json string username: The username.
    :<json string password: Username's password.

    :>json string message: A status message describing the outcome of the request.
    :>json string access_token: A JWT to authenticate the user ``username`` in further requests.
    :>json string refresh_token: A JWT to refresh the ``access_token`` once it expires.

    :reqheader Accept: Supported ``application/json``
    :resheader Content-Type: ``application/json``

    :statuscode 200: no error
    :statuscode 404: ``username`` does not exist
    :statuscode 500: internal server error

.. http:post:: /registration

    Register a new user with given username and password.

    **Example request**

    .. sourcecode:: http 

      POST /registration HTTP/1.1
      Host: example.com 
      Accept: application/json

      {
        "username": "user",
        "password": "pass"
      }

    **Example response**

    .. sourcecode:: http

      HTTP/1.1 200 OK
      Vary: Accept
      Content-Type: application/json

      {
        "message": "User user was created!",
        "access_token": "access_token",
        "refresh_token": "refresh_token",
      }

    :<json string username: The username.
    :<json string password: Username's password.

    :>json string message: A status message describing the outcome of the request.
    :>json string access_token: A JWT to authenticate the user ``username`` in further requests.
    :>json string refresh_token: A JWT to refresh the ``access_token`` once it expires.

    :statuscode 200: no error
    :statuscode 400: given ``username`` is not a valid username
    :statuscode 500: internal server error

Managing multiobjective optimization problems
---------------------------------------------

.. http:post:: /problem/access

    Access an existing problem and fetch its information.

    **Example request**

    .. sourcecode:: http

      POST /problem/access HTTP/1.1
      Host: example.com 
      Accept: application/json

      {
        "problem_id": "1",
      }

    **Example response**

    .. sourcecode:: http

      HTTP/1.1 200 OK
      Vary: Accept
      Content-Type: application/json

      {
        "objective_names": ["f1", "f2", "f3"],
        "variable_names": ["x", "y", "z"],
        "ideal": [100, -20, 0.1],
        "nadir": [20, 20, -0.001],
        "n_objectives": 3,
        "minimize": [-1, 1, -1],
        "problem_name": "Example problem",
        "problem_type": "Analytical",
        "problem_id": 1,
      }

    :<json number problem_id: The id of the problem.
    :reqheader Authorization: An JWT access token. Example ``Bearer <access token>``

    :>json array objective_names: An arrays of strings with objective names.
    :>json array variable_names: An arrays of strings with variable names.
    :>json array ideal: An array of numbers with the ideal point.
    :>json array nadir: An array of numbers with the nadir point.
    :>json number n_objectives: The number of objectives in the problem.
    :>json array minimize: An array of integers being either ``1`` or ``-1``, where ``1`` at the i'th position indicates the the i'th objective is to be minimized and ``-1`` indicated the objective is to be maximized.
    :>json string problem_name: The name given to the problem.
    :>json string problem_type: The type of the problem.
    :>json number problem_id: The id of the problem.

    :statuscode 200: ok, problem fetched successfully
    :statuscode 401: unauthorized, check the access token
    :statuscode 404: problem with given ``problem_id`` not found
    :statuscode 500: internal server error

Create and operate methods for solving multiobjective optimization problems
---------------------------------------------------------------------------
