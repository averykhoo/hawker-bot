import inspect
from typing import Any
from typing import Any
from typing import Any
from typing import Any
from typing import Any
from typing import Any
from typing import Any
from typing import Callable
from typing import Dict
from typing import ForwardRef
from typing import ForwardRef
from typing import cast

from pydantic.typing import ForwardRef, evaluate_forwardref



def get_typed_annotation(param: inspect.Parameter, globalns: Dict[str, Any]) -> Any:
    annotation = param.annotation
    if isinstance(annotation, str):
        annotation = ForwardRef(annotation)
        annotation = evaluate_forwardref(annotation, globalns, globalns)
    return annotation


def get_typed_signature(call: Callable[..., Any]) -> inspect.Signature:
    signature = inspect.signature(call)
    globalns = getattr(call, "__globals__", {})
    typed_params = [
        inspect.Parameter(
            name=param.name,
            kind=param.kind,
            default=param.default,
            annotation=get_typed_annotation(param, globalns),
        )
        for param in signature.parameters.values()
    ]
    typed_signature = inspect.Signature(typed_params)
    return typed_signature



def add_non_field_param_to_dependency(
    *, param: inspect.Parameter, dependant: Dependant
) -> Optional[bool]:
    if lenient_issubclass(param.annotation, Request):
        dependant.request_param_name = param.name
        return True
    elif lenient_issubclass(param.annotation, WebSocket):
        dependant.websocket_param_name = param.name
        return True
    elif lenient_issubclass(param.annotation, HTTPConnection):
        dependant.http_connection_param_name = param.name
        return True
    elif lenient_issubclass(param.annotation, Response):
        dependant.response_param_name = param.name
        return True
    elif lenient_issubclass(param.annotation, BackgroundTasks):
        dependant.background_tasks_param_name = param.name
        return True
    elif lenient_issubclass(param.annotation, SecurityScopes):
        dependant.security_scopes_param_name = param.name
        return True
    return None


def call_endpoint(endpoint:Callable):

    endpoint_signature = get_typed_signature(endpoint)
    signature_params = endpoint_signature.parameters

    for param_name, param in signature_params.items():
        if add_non_field_param_to_dependency(param=param, dependant=dependant):
            continue
        param_field = get_param_field(
            param=param, default_field_info=params.Query, param_name=param_name
        )
        if param_name in path_param_names:
            assert is_scalar_field(
                field=param_field
            ), "Path params must be of one of the supported types"
            if isinstance(param.default, params.Path):
                ignore_default = False
            else:
                ignore_default = True
            param_field = get_param_field(
                param=param,
                param_name=param_name,
                default_field_info=params.Path,
                force_type=params.ParamTypes.path,
                ignore_default=ignore_default,
            )
            add_param_to_fields(field=param_field, dependant=dependant)
        elif is_scalar_field(field=param_field):
            add_param_to_fields(field=param_field, dependant=dependant)
        elif isinstance(
            param.default, (params.Query, params.Header)
        ) and is_scalar_sequence_field(param_field):
            add_param_to_fields(field=param_field, dependant=dependant)
        else:
            field_info = param_field.field_info
            assert isinstance(
                field_info, params.Body
            ), f"Param: {param_field.name} can only be a request body, using Body(...)"
            dependant.body_params.append(param_field)
    return dependant