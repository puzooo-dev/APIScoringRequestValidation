import datetime
import hashlib
import json
import logging
import re
import random
import uuid
from argparse import ArgumentParser
from email.message import Message
from enum import Enum
from http.server import (
    BaseHTTPRequestHandler,
    HTTPServer,
)
from typing import Any, Callable, Dict, List, Optional

# Authentication constants
SALT = "Otus"
ADMIN_LOGIN = "admin"
ADMIN_SALT = "42"

# HTTP status codes
OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
INVALID_REQUEST = 422
INTERNAL_ERROR = 500

# Error messages mapping
ERRORS = {
    BAD_REQUEST: "Bad Request",
    FORBIDDEN: "Forbidden",
    NOT_FOUND: "Not Found",
    INVALID_REQUEST: "Invalid Request",
    INTERNAL_ERROR: "Internal Server Error",
}


class Gender(Enum):
    """Enum for gender values"""

    UNKNOWN = 0
    MALE = 1
    FEMALE = 2


class ErrorMessage(Enum):
    """Standard error messages"""

    BAD_REQUEST = "Bad Request"
    FORBIDDEN = "Forbidden"
    NOT_FOUND = "Not Found"
    INVALID_REQUEST = "Invalid Request"
    INTERNAL_ERROR = "Internal Server Error"


class Field:
    """
    Base descriptor class for all validation fields.

    Implements the descriptor protocol to automatically validate
    values when they are assigned to class attributes.
    """

    def __init__(self, required: bool = False, nullable: bool = False):
        """
        Initialize a field validator.

        Args:
            required: If True, field must be present and non-None
            nullable: If True, None is allowed as a value
        """
        self.required = required
        self.nullable = nullable
        self.field_name = None

    def __set_name__(self, owner, name):
        """
        Called when the descriptor is assigned to a class attribute.
        Stores the field name for error messages.
        """
        self.field_name = name

    def __get__(self, obj, objtype=None):
        """
        Descriptor getter. Returns the value from instance dictionary.
        """
        if obj is None:
            return self
        return obj.__dict__.get(self.field_name, None)

    def __set__(self, obj, value):
        """
        Descriptor setter. Validates the value before storing it.
        """
        validated_value = self.validate(value)
        obj.__dict__[self.field_name] = validated_value

    def validate(self, value: Any) -> Any:
        """
        Base validation logic. Checks required and nullable constraints.

        Args:
            value: The value to validate

        Returns:
            Validated value (may be transformed)

        Raises:
            ValueError: If validation fails
            TypeError: If type check fails
        """
        if value is None:
            if self.required:
                raise ValueError(f"'{self.field_name}' is required")
            if not self.nullable:
                raise ValueError(f"'{self.field_name}' cannot be empty")
            return None

        return value

    def is_empty(self, value: Any) -> bool:
        """
        Check if a value is considered empty.

        Args:
            value: The value to check

        Returns:
            True if value is None, empty string, or empty list
        """
        if value is None:
            return True
        if isinstance(value, str) and value == "":
            return True
        if isinstance(value, list) and len(value) == 0:
            return True
        return False


class CharField(Field):
    """
    String field validator.

    Validates that the value is a string and respects max_length constraint.
    """

    def __init__(
        self, required: bool = False, nullable: bool = False, max_length: int = None
    ):
        super().__init__(required, nullable)
        self.max_length = max_length

    def validate(self, value: Any) -> Optional[str]:
        """
        Validate string value.

        Args:
            value: Value to validate

        Returns:
            Validated string or None

        Raises:
            TypeError: If value is not a string
            ValueError: If max_length is exceeded
        """
        value = super().validate(value)

        if value is None:
            return None

        if not isinstance(value, str):
            raise TypeError(
                f"'{self.field_name}' must be a string, got {type(value).__name__}"
            )

        if self.max_length and len(value) > self.max_length:
            raise ValueError(
                f"'{self.field_name}' cannot be longer than {self.max_length} characters"
            )

        return value


class ArgumentsField(Field):
    """
    Arguments field validator for method arguments.

    Validates that the value is a dictionary.
    """

    def validate(self, value: Any) -> Optional[Dict]:
        """
        Validate dictionary value.

        Args:
            value: Value to validate

        Returns:
            Validated dictionary or None

        Raises:
            TypeError: If value is not a dictionary
        """
        value = super().validate(value)

        if value is None:
            return None

        if not isinstance(value, dict):
            raise TypeError(
                f"'{self.field_name}' must be a dictionary, got {type(value).__name__}"
            )

        return value


class EmailField(CharField):
    """
    Email field validator.

    Validates that the string contains '@' symbol.
    """

    def validate(self, value: Any) -> Optional[str]:
        """
        Validate email format.

        Args:
            value: Value to validate

        Returns:
            Validated email string or None

        Raises:
            ValueError: If '@' is missing
        """
        value = super().validate(value)

        if value is None:
            return None

        if "@" not in value:
            raise ValueError(f"'{self.field_name}' must contain '@' symbol")

        return value


class PhoneField(Field):
    """
    Phone number field validator.

    Validates that phone number has 11 digits and starts with 7.
    Accepts strings or numbers, strips non-digit characters.
    """

    def validate(self, value: Any) -> Optional[str]:
        """
        Validate phone number.

        Args:
            value: Value to validate (string or number)

        Returns:
            Validated phone number as 11-digit string or None

        Raises:
            TypeError: If value is not a string or number
            ValueError: If length is not 11 or doesn't start with 7
        """
        value = super().validate(value)

        if value is None:
            return None

        # Convert number to string if needed
        if isinstance(value, (int, float)):
            value = str(int(value))

        if not isinstance(value, str):
            raise TypeError(
                f"'{self.field_name}' must be a string or number, got {type(value).__name__}"
            )

        # Remove all non-digit characters
        cleaned = re.sub(r"\D", "", value)

        if len(cleaned) != 11:
            raise ValueError(
                f"'{self.field_name}' must contain exactly 11 digits, got {len(cleaned)}"
            )

        if not cleaned.startswith("7"):
            raise ValueError(f"'{self.field_name}' must start with 7, got {cleaned[0]}")

        return cleaned


class DateField(Field):
    """
    Date field validator.

    Validates date in DD.MM.YYYY format.
    """

    def validate(self, value: Any) -> Optional[str]:
        """
        Validate date format.

        Args:
            value: Value to validate

        Returns:
            Validated date string or None

        Raises:
            TypeError: If value is not a string
            ValueError: If date format is invalid
        """
        value = super().validate(value)

        if value is None:
            return None

        if not isinstance(value, str):
            raise TypeError(
                f"'{self.field_name}' must be a string, got {type(value).__name__}"
            )

        try:
            datetime.datetime.strptime(value, "%d.%m.%Y")
        except ValueError:
            raise ValueError(f"'{self.field_name}' must be in DD.MM.YYYY format")

        return value


class BirthDayField(DateField):
    """
    Birthday field validator.

    Validates that age is not more than 70 years.
    """

    def validate(self, value: Any) -> Optional[str]:
        """
        Validate birthday (age <= 70).

        Args:
            value: Value to validate

        Returns:
            Validated date string or None

        Raises:
            ValueError: If age exceeds 70 years
        """
        value = super().validate(value)

        if value is None:
            return None

        birth_date = datetime.datetime.strptime(value, "%d.%m.%Y")
        today = datetime.datetime.now()

        # Calculate age correctly accounting for birthdays not yet passed this year
        age = (
            today.year
            - birth_date.year
            - ((today.month, today.day) < (birth_date.month, birth_date.day))
        )

        if age > 70:
            raise ValueError(f"Age cannot be greater than 70 years, got {age}")

        return value


class GenderField(Field):
    """
    Gender field validator.

    Validates that gender is 0, 1, or 2.
    """

    def validate(self, value: Any) -> Optional[int]:
        """
        Validate gender value.
        Args:
            value: Value to validate
        Returns:
            Validated integer or None
        """
        value = super().validate(value)

        if value is None:
            return None

        # Try to convert to int if not already
        if not isinstance(value, int):
            raise TypeError(
                f"'{self.field_name}' must be a number, got {type(value).__name__}"
            )

        if value not in [0, 1, 2]:
            raise ValueError(f"'{self.field_name}' must be 0, 1, or 2, got {value}")

        return value


class ClientIDsField(Field):
    """
    Client IDs field validator
    """

    def validate(self, value: Any) -> Optional[List[int]]:
        """
        Validate client IDs list.
        Args:
            value: Value to validate
        Returns:
            Validated list of integers or None
        """
        value = super().validate(value)

        if value is None:
            return None

        if not isinstance(value, list):
            raise TypeError(
                f"'{self.field_name}' must be a list, got {type(value).__name__}"
            )

        if len(value) == 0:
            raise ValueError(f"'{self.field_name}' cannot be empty")

        for item in value:
            if not isinstance(item, int):
                raise TypeError(
                    f"'{self.field_name}' must contain only integers, got {type(item).__name__}"
                )

        return value


class ValidationMeta(type):
    """
    Metaclass for request validation classes.

    Automatically collects all Field instances defined in the class
    and stores them in the _fields attribute for later iteration.
    """

    def __new__(mcs, name, bases, namespace):
        """
        Create a new class with collected fields.

        Args:
            name: Class name
            bases: Base classes tuple
            namespace: Class namespace dictionary

        Returns:
            New class with _fields attribute
        """
        fields = {}

        # Collect all Field instances from the class namespace
        for key, value in namespace.items():
            if isinstance(value, Field):
                fields[key] = value

        # Store the collected fields in the class
        namespace["_fields"] = fields
        return super().__new__(mcs, name, bases, namespace)


class BaseRequest(metaclass=ValidationMeta):
    """
    Base class for all request validators.

    Uses the ValidationMeta metaclass to automatically collect fields
    and provides common validation functionality.
    """

    def __init__(self, **kwargs):
        """
        Initialize request with data and validate all fields.

        Args:
            **kwargs: Field values to validate
        """
        self._errors = {}
        self._non_empty_fields = []

        # Validate each field that was defined in the class
        for field_name, field in self._fields.items():
            value = kwargs.get(field_name)

            try:
                # Setattr triggers the descriptor's __set__ method
                setattr(self, field_name, value)

                # Track non-empty fields for context
                if not field.is_empty(value):
                    self._non_empty_fields.append(field_name)

            except (ValueError, TypeError) as e:
                self._errors[field_name] = str(e)

        # Check for extra fields not defined in the class
        extra_fields = set(kwargs.keys()) - set(self._fields.keys())
        if extra_fields:
            for field in extra_fields:
                self._errors[field] = "Unknown field"

    def is_valid(self) -> bool:
        """
        Check if the request is valid.

        Returns:
            True if no validation errors, False otherwise
        """
        return len(self._errors) == 0

    def get_errors(self) -> Dict[str, str]:
        """
        Get all validation errors.

        Returns:
            Dictionary mapping field names to error messages
        """
        return self._errors

    def get_non_empty_fields(self) -> List[str]:
        """
        Get list of fields that have non-empty values.

        Returns:
            List of field names that were provided with non-empty values
        """
        return self._non_empty_fields


class MethodRequest(BaseRequest):
    """
    Method request validator for the main API request wrapper.

    Validates the outer structure of the API request including
    authentication fields and method routing information.
    """

    account = CharField(required=False, nullable=True)
    login = CharField(required=True, nullable=True)
    token = CharField(required=True, nullable=True)
    arguments = ArgumentsField(required=True, nullable=True)
    method = CharField(required=True, nullable=False)

    @property
    def is_admin(self) -> bool:
        """
        Check if the request is from admin user.

        Returns:
            True if login is 'admin', False otherwise
        """
        return self.login == ADMIN_LOGIN


class OnlineScoreRequest(BaseRequest):
    """
    Online score request validator.

    Validates arguments for the online_score method.
    Requires at least one pair of fields: phone-email, first_name-last_name, or gender-birthday.
    """

    first_name = CharField(required=False, nullable=True)
    last_name = CharField(required=False, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)

    def is_valid(self) -> bool:
        if not super().is_valid():
            return False

        has_pair = (
            (self.phone and self.email)
            or (self.first_name and self.last_name)
            or (self.gender is not None and self.birthday)
        )

        if not has_pair:
            self._errors["arguments"] = (
                "At least one pair required: "
                "(phone & email), (first_name & last_name), or (gender & birthday)"
            )

        return len(self._errors) == 0


class ClientsInterestsRequest(BaseRequest):
    """
    Clients interests request validator.

    Validates arguments for the clients_interests method.
    Requires non-empty list of client IDs.
    """

    client_ids = ClientIDsField(required=True, nullable=False)
    date = DateField(required=False, nullable=True)


def get_score(
    phone: Optional[str] = None,
    email: Optional[str] = None,
    birthday: Optional[str] = None,
    gender: Optional[int] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
) -> float:
    """
    Calculate credit score based on provided data.

    Args:
        phone: Phone number
        email: Email address
        birthday: Birth date in DD.MM.YYYY format
        gender: Gender (0, 1, or 2)
        first_name: First name
        last_name: Last name

    Returns:
        Calculated score as float
    """
    score = 0.0

    if phone:
        score += 1.5

    if email:
        score += 1.5

    if birthday and gender is not None:
        score += 1.5

    if first_name and last_name:
        score += 0.5

    return score


def get_interests(cid: str) -> List[str]:
    """
    Generate random interests for a client.

    Args:
        cid: Client ID (used as seed for reproducibility)

    Returns:
        List of 2 random interests
    """
    interests = [
        "cars",
        "pets",
        "travel",
        "hi-tech",
        "sport",
        "music",
        "books",
        "tv",
        "cinema",
        "geek",
        "otus",
    ]

    # Use cid as seed for deterministic results per client
    random.seed(hash(cid))
    result = random.sample(interests, 2)
    random.seed()  # Reset seed
    return result


def check_auth(request: MethodRequest) -> bool:
    """
    Check authentication token validity.

    For admin user, uses hourly rotating token based on ADMIN_SALT.
    For regular users, uses HMAC-like token based on account+login+SALT.

    Args:
        request: Validated MethodRequest instance

    Returns:
        True if token is valid, False otherwise
    """
    if request.is_admin:
        expected = hashlib.sha512(
            (datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT).encode("utf-8")
        ).hexdigest()
    else:
        account = request.account or ""
        login = request.login or ""
        expected = hashlib.sha512((account + login + SALT).encode("utf-8")).hexdigest()

    return expected == request.token


def handle_online_score(
    arguments: Dict[str, Any], ctx: Dict[str, Any], is_admin: bool
) -> tuple[Dict[str, Any], int]:
    """
    Handle online_score method request.

    Args:
        arguments: Method arguments dictionary
        ctx: Context dictionary for logging
        is_admin: Whether the user is admin

    Returns:
        Tuple of (response_data, http_status_code)
    """
    # Validate arguments
    score_req = OnlineScoreRequest(**arguments)

    if not score_req.is_valid():
        errors = score_req.get_errors()
        error_msg = "; ".join([f"{k}: {v}" for k, v in errors.items()])
        return {"error": error_msg}, INVALID_REQUEST

    # Store non-empty fields in context for logging
    ctx["has"] = score_req.get_non_empty_fields()

    # Admin always gets maximum score
    if is_admin:
        return {"score": 42}, OK

    # Calculate score based on provided data
    score = get_score(
        phone=score_req.phone,
        email=score_req.email,
        birthday=score_req.birthday,
        gender=score_req.gender,
        first_name=score_req.first_name,
        last_name=score_req.last_name,
    )

    return {"score": score}, OK


def handle_clients_interests(
    arguments: Dict[str, Any], ctx: Dict[str, Any]
) -> tuple[Dict[str, Any], int]:
    """
    Handle clients_interests method request.

    Args:
        arguments: Method arguments dictionary
        ctx: Context dictionary for logging

    Returns:
        Tuple of (response_data, http_status_code)
    """
    # Validate arguments
    interests_req = ClientsInterestsRequest(**arguments)

    if not interests_req.is_valid():
        errors = interests_req.get_errors()
        error_msg = "; ".join([f"{k}: {v}" for k, v in errors.items()])
        return {"error": error_msg}, INVALID_REQUEST

    # Store number of clients in context for logging
    ctx["nclients"] = len(interests_req.client_ids)

    # Generate interests for each client
    result = {}
    for client_id in interests_req.client_ids:
        result[str(client_id)] = get_interests(str(client_id))

    return result, OK


def method_handler(
    request: Dict[str, Any], ctx: Dict[str, Any], settings: Dict[str, Any] = None
) -> tuple[Dict[str, Any], int]:
    """
    Main method handler for API requests.

    Validates the request wrapper, authenticates the user,
    and routes to the appropriate method handler.

    Args:
        request: Request dictionary with 'body' and 'headers' keys
        ctx: Context dictionary for logging
        settings: Server settings (unused, kept for compatibility)

    Returns:
        Tuple of (response_data, http_status_code)
    """
    body = request.get("body", {})

    # Step 1: Validate the base request structure
    method_req = MethodRequest(**body)

    if not method_req.is_valid():
        errors = method_req.get_errors()
        error_msg = "; ".join([f"{k}: {v}" for k, v in errors.items()])
        return {"error": error_msg}, INVALID_REQUEST

    # Step 2: Authenticate the user
    if not check_auth(method_req):
        return {"error": "Forbidden"}, FORBIDDEN

    # Step 3: Route to specific method handler
    method = method_req.method
    arguments = method_req.arguments or {}

    if method == "online_score":
        return handle_online_score(arguments, ctx, method_req.is_admin)

    elif method == "clients_interests":
        return handle_clients_interests(arguments, ctx)

    else:
        return {"error": f"Unknown method: {method}"}, INVALID_REQUEST


class MainHTTPHandler(BaseHTTPRequestHandler):
    """
    Main HTTP request handler for the scoring API.

    Handles POST requests to /method endpoint,
    processes JSON requests, and returns JSON responses.
    """

    router: Dict[str, Callable] = {"method": method_handler}

    def get_request_id(self, headers: Message) -> str:
        """
        Get or generate request ID for tracking.

        Args:
            headers: HTTP headers dictionary

        Returns:
            Request ID from X-Request-Id header or new UUID
        """
        return headers.get("HTTP_X_REQUEST_ID", uuid.uuid4().hex)

    def do_POST(self) -> None:
        """
        Handle POST request.

        Parses JSON body, routes to method handler,
        and returns JSON response with appropriate status code.
        """
        response, code = {}, OK
        context = {"request_id": self.get_request_id(self.headers)}
        request = None

        # Parse request body
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            data_string = self.rfile.read(content_length)
            request = json.loads(data_string)
        except Exception:
            code = BAD_REQUEST
            response = {"error": ERRORS.get(BAD_REQUEST, "Bad Request")}

        # Process valid request
        if request:
            path = self.path.strip("/")
            logging.info(f"{self.path}: {data_string} {context['request_id']}")

            if path in self.router:
                try:
                    response, code = self.router[path](
                        {"body": request, "headers": self.headers},
                        context,
                        getattr(self.server, "settings", {}),
                    )
                except Exception as e:
                    logging.exception(f"Unexpected error: {e}")
                    code = INTERNAL_ERROR
                    response = {
                        "error": ERRORS.get(INTERNAL_ERROR, "Internal Server Error")
                    }
            else:
                code = NOT_FOUND
                response = {"error": ERRORS.get(NOT_FOUND, "Not Found")}

        # Send response
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

        # Format response according to API spec
        if code == OK:
            r = {"response": response, "code": code}
        else:
            error_msg = response.get("error", ERRORS.get(code, "Unknown Error"))
            r = {"error": error_msg, "code": code}

        # Log the response
        context.update(r)
        logging.info(context)

        # Write response body
        self.wfile.write(json.dumps(r, ensure_ascii=False).encode("utf-8"))


if __name__ == "__main__":
    """
    Main entry point for the scoring API server.
    Usage:
        python api.py [-p PORT] [-l LOG_FILE]

    Examples:
        python api.py -p 8080
        python api.py -p 8080 -l server.log
        python api.py --port 9000 --log /var/log/api.log
    """
    parser = ArgumentParser(description="Scoring API Server")
    parser.add_argument(
        "-p", "--port", action="store", type=int, default=8080, help="Port to listen on"
    )
    parser.add_argument(
        "-l",
        "--log",
        action="store",
        default=None,
        help="Log file path (default: stdout)",
    )
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        filename=args.log,
        level=logging.INFO,
        format="[%(asctime)s] %(levelname).1s %(message)s",
        datefmt="%Y.%m.%d %H:%M:%S",
    )

    # Start server
    server = HTTPServer(("localhost", args.port), MainHTTPHandler)
    logging.info(f"Starting server on port {args.port}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info("Server stopped by user")
        pass

    server.server_close()
