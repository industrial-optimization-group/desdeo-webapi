HTTP endpoints
==============

.. toctree
    :maxdepth: 3
    :caption: Contents

Login and Registration
----------------------

Logging in
^^^^^^^^^^

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

Registering
^^^^^^^^^^^

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

Accessing an existing problem
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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


Query supported problem types
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /problem/create

    Query for the supported problem types.
  
    **Example request**
  
    .. sourcecode:: http

      GET /problem/create HTTP/1.1
      Host: example.com

    **Example response**

    .. sourcecode:: http

      HTTP/1.1 200 OK
      Vary: Accept
      Content-Type: application/json

      {
        "available_problem_types": ["Analytical", "Discrete"],
      }
    
    :reqheader Authorization: A JWT access token. Example ``Bearer <access token>``

    :>json array available_problem_types: An array of strings with the supported problem type names.

    :statuscode 200: ok

Create a new problem
^^^^^^^^^^^^^^^^^^^^

.. http:post:: /problem/create

    Define a new multiobjective optimization problem.

    .. note::
      
      Currently only problems with analytical or discrete formulations are supported.

    **Example request (Discrete problem)**

    Here we define a discrete problem with two variables and three (minimized) objectives with
    four variable and objective vector pairs.

    .. sourcecode:: http

      POST /problem/create HTTP/1.1
      Host: example.com
      Accept: application/json

      {
        "problem_type": "Discrete",
        "name": "Discrete problem",
        "objectives": [[1,2,3], [4,5,6], [7,8,9], [10,11,12]],
        "objective_names": ["z_1", "z_2", "z_3"],
        "variables": [[1,2], [3,4], [5,6], [7,8]],
        "variable_names": ["x_1", "x_2"],
        "ideal": [0,0,0],
        "nadir": [10, 10, 10],
        "minimize": [1, 1, 1],
      }

    .. note::
      
      The variable and objectie vector pairs are expected to match one-to-one. In other words, it is assumed that
      :math:`f(\mathbf{x}_i) = \mathbf{z}_i`, where :math:`i` is the position of the variable vector :math:`\mathbf{x}_i`
      in the entry *variables* and the position of the objective vector :math:`\mathbf{z}_i` in the entry
      *objectives*.

    **Example request (Analytical problem)**

    Here we define a problem with two variables and three objectives as follows:

    .. math::

      &\text{min}\,f_1(x, y, z) &= x + y \\
      &\text{max}\,f_2(x, y, z) &= x - z \\
      &\text{min}\,f_3(x, y, z) &= x + y +z \\
      &&\text{s.t.}\, x, y, z \in [-10, 10]

    .. sourcecode:: http

      POST /problem/create HTTP/1.1
      Host: example.com
      Accept: application/json

      {
        "problem_type": "Analytical",
        "name": "Analytical problem",
        "objective_functions": ["x+y", "x-z", "z+y+x"],
        "objective_names": ["f1", "f2", "f3"],
        "variables": ["x", "y", "z"],
        "variable_initial_values": [0, 0, 0],
        "variable_bounds": [[-10, 10], [-10, 10], [-10, 10]],
        "variable_names": ["x", "y", "z"],
        "ideal": [10, 20, 30],
        "nadir": [-10, -20, -30],
        "minimize": [1, -1, 1],
      }

    .. note::

      The *variable_names* must each be found in the expressions contained in
      *objective_functions*.  Currently only simple expressions with single
      character variables and basic artihmetic operators (+, -, /, \*) have been tested.
      The function expressions are parsed using Sympy.

    .. warning::

      The function expressions are parsed using Sympy.

    **Example response (problem created)**

    .. sourcecode:: http 

      HTTP/1.1 201 Created
      Vary: Accept
      Content-Type: application/json

      {
        "problem_type": "type"
        "name": "name of the problem",
        "owner": "username of the user the problem belongs to",
      }

    **Example response (something goes wrong)**

    .. sourcecode:: http

      HTTP/1.1 406 Not acceptable
      Vary: Accept
      Content-Type: application/json

      {
        "message": "Informative message telling what went wrong.",
      }

    :reqheader Authorization: A JWT access token. Example ``Bearer <access token>``
    
    :>json string problem_type: A string with the name of the problem type being defined.
    :>json string name: The name of the problem.
    :>json array objective_functions: (**only for analytical problems**) an array of string expressions representing objective functions.
    :>json array objective_names: An array of strings with the names on individual objectives. 
    :>json array variables: **Analytical problems**: an array of single and unique characters representing the variable symbols in *objective_functions*.
      **Discrete problems**: an array of arrays whre each inner element represents one instance of a variable vector.
    :>json array variable_initial_values: (**only for analytical problems**) an array of numbers with the initial values for each variable.
    :>json array variable_bounds: (**only for analytical problems**) an array of tuples with each tuple representing the lower and upper bounds of the variables.
    :>json array variable_names: An array with the names of the variables.
    :>json array ideal: (optional) the ideal point of the problem.
    :>json array nadir: (optional) the nadir point of the problem.
    :>json array minimize: An array with one element for each objective and where each element is either 1 or -1, where 1 indicates and objective to be minimized and
      -1 indicates an objective to be maximized. 
    :>json array objectives: (**only discrete problems**) an array of arrays where each inner element represents one instance of an objective vector.

    :<json string problem_type: The type of the created problem.
    :<json string name: The name of the created problem.
    :<json string owner: The username of the owner of the created problem.

    :statuscode 201: Created, problem was successfully created.

    :statuscode 406: Not acceptable, something in the request is not valid. Check the ``message`` entry in the response for additional details.
    :statuscode 500: Internal server error, something went wrong while parsing the request. Check the ``message`` entry in the response for additional details.

Fetch solutions from an archive
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Solutions related to defined problems can be saved and fetched from the
database. Currently, only a single archive of solutions can exists for each
problem.

.. http:get:: /archive

  Fetch problems from the archive for a specific problem. Example with
  a problem with 3 variables and 2 objectives.
  
  **Exmaple request**

  .. sourcecode:: http

    GET /archive HTTP/1.1
    Host: example.com
    Accept: application/json

    {
      "problem_id": 1,
    }
  
  **Example response**

  .. sourcecode:: http

    HTTP/1.1 200 OK
    Vary: Accept
    Content-Type: application/json

    {
      "variables": [[1.1, 2.2, 3.3], [1.2, 3.1, 2.2], [0.4, 1.2, 1.7]],
      "objectives": [[0.5, 0.7], [0.3, 0.8], [0.9, 0.1]],
      "info": "These solutions are interesting.",
      "date": "1/1/2022 -- 11:11:11",
    }
  
  :reqheader Authorization: A JWT access token. Example ``Bearer <access token>``

  :<json number problem_id: The id of the problem which solutions should be fetched.

  :>json array variables: An array of arrays with variable vectors.
  :>json array objectives: An array of array with objective vectors.
  :>json string info: A string containing info related to the archive.
  :>json string date: A date indicateing the last time the archive was modified. The date is in the format ``%d/%m/%Y -- %H:%M:%S``.

  .. note::

    The variable vectors and objective vectors are matched by index. In other
    words, evaluating a variable vector at position ``i`` in ``variables`` will result in an
    objective vector at position ``i`` in ``objectives``.

  :statuscode 200: ok, solutions returned as requested.
  :statuscode 404: not found, either no problem with the specified id
    exists for the current user or the archive is empty.
    
Add solutions to an archive
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Add solutions to an archive for a specific problem. Example for problem
with 3 variables and 2 objectives.

.. http:post:: /archive

  **Example request**

  .. sourcecode:: http

    POST /archive HTTP/1.1
    Host: example.com
    Accept: application/json

    {
      "problem_id": 1,
      "variables": [[1.1, 2.2, 3.3], [1.2, 3.1, 2.2], [0.4, 1.2, 1.7]],
      "objectives": [[0.5, 0.7], [0.3, 0.8], [0.9, 0.1]],
      "append": true,
      "info": "Info about the added solutions.",
    }

  **Example response**

  .. sourcecode:: http

    HTTP/1.1 201 OK
    Vary: Accept
    Content-Type: application/json

    {
      "message": "Created new archive for problem with id 1 and added solutions.",
    }

  :reqheader Authorization: A JWT access token. Example ``Bearer <access token>``

  :<json number problem_id: The id of the problem which solutions should be fetched.
  :<json array variables: An array of arrays with variable vectors.
  :<json array objectives: An array of array with objective vectors.
  :<json boolean append: Whether to append the solution to an existing archive or
    change the content of the archive to the sent solutions. Defaults to true.
  :<json string info: Info related to the solutions added. Optional. If ``append`` was true, then 
    the contents of info will be appended to the existing info, if any. If ``append`` was false, then
    the contents of info will replace the existing info in the archive.

  .. note::

    The variable vectors and objective vectors are matched by index. In other
    words, evaluating a variable vector at position ``i`` in ``variables`` will result in an
    objective vector at position ``i`` in ``objectives``. Therefore, the number variable
    and objective vectors should match.

  .. warning::

    Setting ``append`` to ``false`` will result in the existing archive to be wiped and
    replaced by the solutions sent in the request! If the solutions are to be *added* to the
    archive, ``append`` should be set to ``true``.

  :>json string message: A message with additional details.

  :statuscode 201: created, a new archive was created and solutions were added to it.
  :statuscode 202: accepted, the solutions were either appended to an existing archive
    the old archive was replaced by the new solution. Check ``message`` for additional details.
  :statuscode 400: bad request, the number of variable vectors does not match with
    the number of objective vectors.
  :statuscode 404: not found, the problem with id ``problem_id`` was not found.


Setup an interactive method for solving multiobjective optimization problems
----------------------------------------------------------------------------

Check if an active method exists
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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

Initialize a new interactive method
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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

Starting a method
^^^^^^^^^^^^^^^^^

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

Iterating methods
^^^^^^^^^^^^^^^^^

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

E-NAUTILUS
----------

When E-NAUTILUS is first started, the first request returned by E-NAUTILUS will look as
the example shown below:

.. sourcecode:: json

  {
    "response": {
      "message": "...",
      "ideal": "[0.4, 0.9, 0.11]",
      "nadir": "[5.9, 9.8, 12.3]",
    },
  }

The `ideal` and `nadir` entries will show the best and worst reachable values from the starting point, which
in E-NAUTILUS is the nadir point. As a response to this request, a JSON object with the following contents is 
expected (with example values):

.. sourcecode:: json

  {
    "response": {
      "n_iterations": 10,
      "n_points": 3,
    },
  }

In the above object, `n_iterations` is the number of total iterations that should be taken in the E-NAUTILUS method
and `n_points` is the number of intermediate points shown in each iteration. The number of iterations may be changed
during the course of the method.

After E-NAUTILUS has been initialized by providing the above response to the first request, subsequent requests will have the 
following (example) contents:

.. sourcecode:: json

  {
    "response": {
      "message": "...",
      "ideal": "[0.4, 0.9, 0.11]",
      "nadir": "[5.9, 9.8, 12.3]",
      "points": "[[1.2, 3.2, 2.2], [0.8, 3.1, 3.9]]",
      "lower_bounds": "[[0.9, 1.2, 2.2], [0.5, 1.1, 1.9]]",
      "upper_bounds": "[[3.9, 3.2, 4.2], [3.5, 3.1, 4.9]]",
      "n_iterations_left": 4,
      "distances": "[0.66, 0.56]",
    },
  }

In these requests, the entry `points` will be a 2-dimensional array with the intermediate points returned by E-NAUTILUS
in an intermediate iteration. Likewise, `lower_bounds` and `upper_bounds` are the lower and upper bounds of the reachable
from each intermediate point. `n_iterations_left` is the number of iterations left and `distances` are the distances (0-100,
zero being farthest from the Pareto front and 100 being closest) of each intermediate point to the Pareto optimal
front. `points`, `lower_bounds`, and `upper_bounds` are ordered by index, meaning that the bounds of the point at index `n`
in `points` are located at index `n` in `lower_bounds` and `upper_bounds`, respectively.

The response expected to the above type of requests should have the following fields (with examples given):

.. sourcecode:: json

  {
    "response": {
        "preferred_point_index": 1,
        "step_back": false,
        "change_remaining": true,
        "iterations_left": 5,
    },
  }

Above, `preferred_point_index` is the index of the point in `points` which should be selected for the next
iteration in E-NAUTILUS. `step_back` indicates that the method should go back to a previous iteration.
`change_remaining` indicates that the remaining number of iterations should be changed. `iterations_left` is
required only when either `step_back` or `change_remaining` is ``true``.

.. note::

  When stepping back in E-NAUTILUS (i.e., `step_back` is set to ``true``), a response with the follwoing
  example contents
  is expected:

  .. sourcecode:: json

    {
      "response": {
          "preferred_point_index": "...",
          "step_back": true,
          "change_remaining": "...",
          "prev_solutions": "[[1.2, 3.2, 2.2], [0.8, 3.1, 3.9]]",
          "prev_lower_bounds": "[[0.9, 1.2, 2.2], [0.5, 1.1, 1.9]]",
          "prev_upper_bounds": "[[3.9, 3.2, 4.2], [3.5, 3.1, 4.9]]",
          "iterations_left": 3,
          "prev_distances": "[0.66, 0.56]",
      }
    }

  In other words, the full state of the E-NAUTILUS method in the previous iterations, to which
  we wish to return, must be supplied is the response. It is therefore
  a good idea to keep track of previous
  states in any application making use of this API.

When E-NAUTILUS is iterated for the last time, a request with the following example contents is
returned:

.. sourcecode:: json

  {
    "response": {
      "message": "...",
      "solution": "[1.0, 1.1, 1.2]",
    },
  }

The `solution` entry contains the final (Pareto optimal) solution found by the E-NAUTILUS
method in the objective space of the problem being solved.

.. note::
  
  At the moment, only the objective values of the solution are returned.

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