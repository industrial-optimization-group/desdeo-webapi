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

    :reqheader Authorization: A JWT access token. Example ``Bearer <access token>``
    :<json number problem_id: The id of the problem.

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

Setup an interactive method for solving multiobjective optimization problems
----------------------------------------------------------------------------

.. http:get:: /method/create

  Check if a method has already been defined.

  **Example request**

  .. sourcecode:: http

    GET /method/create HTTP/1.1
    Host: example.com

  **Example response**

  .. sourcecode:: http

    HTTP/1.1 200 OK
    Vary: Accept
    Content-Type: application/json

    {
      "message": "Method found!", 
    }

  :reqheader Authorization: A JWT access token. Example ``Bearer <access token>``

  :>json object response: A JSON-object with a ``message`` (*string*) entry revealing if a method has been defined.

  :statuscode 200: ok, a method has been defined
  :statuscode 404: no defined method found

.. http:post:: /method/create

  Initialize a new interactive method with an existing problem.

  .. note::

    For now, setting initialization parameters of interactive methods using the web API
    is not supported. This feature is work in progress.

  **Example request**

  .. sourcecode:: http

    POST /method/create HTTP/1.1
    Host: example.com
    Accept: application/json

    {
      "problem_id": 0,
      "method": "reference_point_method",
    }

  **Example response**

  .. sourcecode:: http

    HTTP/1.1 201 Created
    Vary: Accept
    Content-Type: application/json

    {
      "method": "reference_point_method",
      "owner": "username",
    }

  :reqheader Authorization: A JWT access token. Example ``Bearer <access token>``
  :<json number problem_id: The id of the problem the method should be initialized with.

  :>json string method: The name of the initialized method.
  :>json string owner: The username of the initialized method's owner.

  :statuscode 201: created, the method was initialized successfully
  :statuscode 404: not found, either no method with the given name in ``method`` was found or no problem with id ``problem_id`` was found.
    See the ``message`` entry in the response for additional details.
  :statuscode 406: not acceptable, returned in the case, for example, when an attempt has been made to initialize a method
    with a problem of an unsupported type. For example, this code will be returned if NAUTILUS Navigator is attempted
    to be initialized with a problem of an analytical type.
  :statuscode 500: internal server error, something went wrong when attempting to initialize the method.

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

.. note::

  For EA methods, sometimes a 'response' field will not be present. See `RVEA`_.

Below, a short summary of the contents of these JSON objects is given for some
methods.  For additional information, one should check DESDEO's documentation
for the different methods both in `desdeo-mcdm's documentation
<https://desdeo-mcdm.readthedocs.io/en/latest/>`_ and in `desdeo-emo's
documentation <https://desdeo-emo.readthedocs.io/en/latest/index.html>`_.

NAUTILUS Navigator
------------------

The requests returned by 'GET' and 'POST' contain
a JSON object with contents as shown below:

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

RVEA
----

.. warning::

  For the time being, setting the initialization parameters for RVEA is not
  possible using the web API.  This means that default values will be used. See
  `RVEA in desdeo-emo's documenation
  <https://desdeo-emo.readthedocs.io/en/latest/autoapi/desdeo_emo/EAs/RVEA/index.html#desdeo_emo.EAs.RVEA.RVEA>`_
  for the default values. **RVEA will be initialized in its interactive form when used through the web API.**

The requests returned by `GET` and `POST` contain a JSON object with both a `response` and
`preference_type` field. An example of a JSON object returned by RVEA is shown below:

.. sourcecode:: json

  {
    "response":
    [{
      "message": "...",
      "validator": "...",
    }, {
      "message": "...",
      "validator": "...",
    }, {
      "message": "...",
      "validator": "...",
      "dimensions_data": "...",
    }, {
      "message": "...",
      "validator": "...",
      "dimensions_data": "...",
    }],
    "preference_type": "integer value",
    "individuals": "...",
    "objectives": "...",
  }

The `validator` in the above response field in the JSON is a string with the name of the validator, which is used
internally in DESDEO. Its use in a front-end application will be informative at best. On the
other hand, `dimensions_data` contains useful information regarding individual objectives. An example of the contents
of `dimensions_data` is as follows:

.. sourcecode:: json

  {
    "dimensions_data":
    {
      "('f1',)":
      {
        "minimize": 1,
        "ideal": "some_value",
        "nadir": "some_value",
      },
      "('f2',)":
      {
        "minimize": 1,
        "ideal": "some_value",
        "nadir": "some_value",
      },
    }
  }

In the above JSON object, the example contains `dimensions_data` for two objectives. Depeding on the problem, the
names and number of objectives will vary.

The `individuals` and `objectives` fields contain the population (i.e., the individual decision variable vectors)
and objective vector associated with each individual, respectively.

.. note::

  The `individuals` and `objectives` returned in requests from intermediatre iterations
  are not necessarely non-dominated. When stopping the method (see below) returned solutions
  will be non-dominated.

The `preference_type` field is used to indicate which kind of preference information is given in a response
returned from a client side application (i.e., in a `POST` request). In other words, this integer valued field is 
used to select one of the responses in the list of objects in the `response` field in the JSON file at the beginning of
this subsection. A positive integer value for `preference_type` will be understood as a selection of a preference type
while a value of '-1' will be understood as a request to stop the method and end iterating. A stop request will
return the final population (i.e., decision variable vectors) and their associated objective vectors in a JSON file
as shown:

.. sourcecode:: json

  {
    "individuals": ["list elements"],
    "objectives": ["list elements"],
  }

.. note::

  The `individuals` and `objectives` returned when stopping the mehtod will be non-dominated. Notice also that there is no
  `response` field when stopping the method (this is to keep a consistent logic of having these two fields at "the top level" of 
  the JSON objects, like in the ones returned from iterating the method).

When iterating RVEA (a `POST` request is made to the server), a JSON file with the following contents is expected in the request:

.. sourcecode:: json

  {
    "response":
    {
      "preference_data": "some data",
      "preference_type": "integer value",
    },
  }

In the above, the `preference_type` field is the same as discussed previously. The `preference_data` field
contains preference information, which varies depending on the specified `preference_type`.

For example, if preference is to be given by choosing available solutions from a list as indices
of those solutions, the above JSON object might look as follows:

.. sourcecode:: json

  {
    "response":
    {
      "preference_data": [2,4,1],
      "preference_type": 0,
    },
  }

Other types of preference available are: specifying indices of solution which
are *not* preferred, specifying a reference point, and specifying a desired
range for each objective as upper and lower bound pairs. Examples of JSON
objects with different kinds of preference types for a problem with three
objectives are as follows:

Specifying indices of solutions which are *not* preferred:

.. sourcecode:: json

  {
    "response":
    {
      "preference_data": [6,10,42],
      "preference_type": 1,
    },
  }

Specifying a reference point:

.. sourcecode:: json

  {
    "response":
    {
      "preference_data": [0.2, 0.5, 0.1],
      "preference_type": 2,
    },
  }

Specifying a desired range for each objective as upper and lower bound pairs:

.. sourcecode:: json

  {
    "response":
    {
      "preference_data":
      [
        [0.3, 0.6],
        [0.2, 0.3],
        [0.9, 1.0],
      ],
      "preference_type": 3,
    },
  }

.. note::

  For a more detailed discussion on the various preference types, please see the related page
  in desdeo-emo's documentation: `Interaction in EAs <https://desdeo-emo.readthedocs.io/en/latest/notebooks/Example.html#Interaction-in-EAs>`_.