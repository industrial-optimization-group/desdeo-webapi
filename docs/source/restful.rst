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

    :statuscode 200: logged in as ``username``
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

    :statuscode 200: new user registered
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

Create interactive methods for solving multiobjective optimization problems
---------------------------------------------------------------------------
TBD

Operate interactive methods for solving multiobjective optimization problems
----------------------------------------------------------------------------

.. http:get:: /method/control

    Start iterating a previously defined method. In practice, we call the ``start()`` method of an interactive method in DESDEO
    and return the first request (not to be confused with an HTTP request) resulting from the method call to ``start()``.
    The ``GET`` request should have no body, only the Authorization header. This works because only one method per user 
    can be active at any given time. It is therefore enough to only know the identity of the user.

    **Example request**

    .. sourcecode:: http

      GET /method/control HTTP/1.1
      Host: example.com 

    **Example response**

    .. sourcecode:: http

      HTTP/1.1 200 OK
      Vary: Accept
      Content-Type: application/json

      {
        "response": {"message": "Helpful message", "..."},
      }

    :reqheader Authorization: A JWT access token. Example ``Bearer <access token>``

    :>json object response: A JSON-object with varying contents. Refer to the ``message`` entry of the ``response``
      for additional information. 

    :statuscode 200: ok, method started
    :statuscode 400: the currently active method has already been started
    :statuscode 401: unauthorized, check the access token
    :statuscode 404: no defined method found for the current user

.. http:post:: /method/control

    After a method has been defined and started (using the above ``GET`` HTTP endpoint), the method may be iterated further
    through ``POST`` requests. In the request, information to continue iterating the method needs to be supplied as specified
    in the previous request's `message` entry. See the section below for additional  details.

    **Example request**

    .. sourcecode:: http

      POST /problem/control HTTP/1.1
      Host: example.com
      Accept: application/json

      {
        "response": {"message": "Helpful message", "other relevant content", "..."},
      }

    **Example response**

    .. sourcecode:: http

      HTTP/1.1 200 OK
      Vary: Accept
      Content-Type: application/json

      {
        "response": {"message": "Helpful message", "information used to continue iterating the method", "..."},
      }

    :reqheader Authorization: A JWT access token. Example ``Bearer <access token>``

    :>json object response: A JSON-object with varying contents. Refer to the ``message`` entry of the ``response``
      for additional information. 

    :statuscode 200: ok, method iterated
    :statuscode 400: method has not been started using a 'GET' request or the previous request (returned by the method) does not exist.
    :statuscode 404: no defined method found for the current user.
    :statuscode 500: could not iterate the method for some internal reason in DESDEO.

Controlling different methods
=============================

When iterated, each 'GET' and 'POST' call to interactive methods will return a JSON object with at least the field 'response'.
This field will contain
all the relevant information that is needed to show information about the problem being solved and the state of the 
interactive method. This information can then be used, for example, to show relevant visualizations in a graphical user interface.

Below, a short summary of the contents of these JSON objects is given. For additional information, one should check DESDEO's
documentation for the different methods.

NAUTILUS Navigator
------------------

The request returned by 'GET' and 'POST' will
return a JSON object with contents as shown below:

.. sourcecode:: json

  {
    "response":
    {
      "message": "...",
      "ideal": "...",
      "nadir": "...",
      "reachable_lb": "...",
      "reachable_ub": "...",
      "user_bounds": "...",
      "reachable_idx": "...",
      "step_number": "...",
      "steps_remaining": "...",
      "distance": "...",
      "allowed_speeds": "...",
      "current_speed": "...",
      "navigation_point": "...",
    },
  }

Most of the information in the above JSON object can be used to show the user information related to the problem being solved.
Not all entries are necessarily relevant or defined. However, the entries 'ideal', 'nadir', 'reachable_lb', 'reachable_ub', 'step_number',
and 'steps_remaining' are always defined. The default number of steps taken in NAUTILUS Navigator defaults to '100', which should be kept
in mind when using the method.

To continue iterating, NAUTILUS Navigator expects a response in subsequent 'POST' requests with the following JSON contents defined:

.. sourcecode:: json

  {
    "response":
    {
      "reference_point": "...",
      "speed": "...",
      "go_to_previous": "...",
      "stop": "...",
      "user_bounds": "...",
    },
  }

Each of these fields must always be defined. User bounds may default to 'NaN's as long as the dimension of the array
matches the number of objectives present in the multiobjective optimization problem being solved. Notice that if a step
is taken backwards, the response supplied in the 'POST' request by the caller must also contain that step's original information
present in that step's original response. I.e., if a step is to be taken backwards from step number x to step y (y < x), then the response from
x must contain all the information that was present in the original response in step y returned by the API (the fields 'ideal', 'nadir',
'reachable_lb', etc...).

.. note::
  It is a good idea to store the information in each of the JSON objects returned by the requests issued by a client so that
  stepping back is possible to any point from the current point.