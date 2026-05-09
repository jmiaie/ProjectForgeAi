import importlib
import inspect
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any


class NativeIntegrationError(RuntimeError):
    pass


def load_symbol(spec: str, source_path: str | None = None) -> type:
    if source_path:
        resolved = str(Path(source_path).expanduser().resolve())
        if resolved not in sys.path:
            sys.path.insert(0, resolved)

    module_name, separator, symbol_name = spec.partition(":")
    if not separator or not module_name or not symbol_name:
        raise NativeIntegrationError(f"Invalid native integration spec: {spec}")

    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        raise NativeIntegrationError(f"Could not import {module_name}") from exc

    try:
        symbol = getattr(module, symbol_name)
    except AttributeError as exc:
        raise NativeIntegrationError(f"{module_name} does not export {symbol_name}") from exc

    if not inspect.isclass(symbol):
        raise NativeIntegrationError(f"{spec} must point to a class")
    return symbol


def instantiate_with_path(cls: type, path_kwarg: str, path: str) -> Any:
    try:
        signature = inspect.signature(cls)
    except (TypeError, ValueError):
        return cls(path)

    parameters = signature.parameters
    if path_kwarg in parameters:
        return cls(**{path_kwarg: path})
    if any(param.kind == inspect.Parameter.VAR_KEYWORD for param in parameters.values()):
        return cls(**{path_kwarg: path})
    if "path" in parameters:
        return cls(path=path)
    if len(parameters) == 0:
        instance = cls()
        if hasattr(instance, path_kwarg):
            setattr(instance, path_kwarg, path)
        return instance
    return cls(path)


async def maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


async def call_first_available(target: Any, method_names: tuple[str, ...], *args: Any, **kwargs: Any) -> Any:
    for method_name in method_names:
        method: Callable[..., Any] | None = getattr(target, method_name, None)
        if method is None:
            continue
        return await maybe_await(method(*args, **kwargs))
    raise NativeIntegrationError(
        f"{target.__class__.__name__} must implement one of: {', '.join(method_names)}"
    )
