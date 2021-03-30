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

Create and operate methods for solving multiobjective optimization problems
---------------------------------------------------------------------------
