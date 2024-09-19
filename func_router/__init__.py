import inspect
from collections import defaultdict
from typing import Optional, Union, get_origin, get_args


def get_full_method_name(method):
    """获取方法的全名，包含模块名和类名（如果有）。"""
    module = method.__module__
    qualname = method.__qualname__
    return f"{module}.{qualname}"


def match_optional_type(param_value, param_type):
    """匹配 Optional 类型的参数。"""
    origin_type = get_origin(param_type)
    if origin_type is Union and type(None) in get_args(param_type):
        return param_value is None or match_type(param_value, get_args(param_type)[0])
    return False


def match_union_type(param_value, param_type):
    """匹配 Union 类型的参数。"""
    origin_type = get_origin(param_type)
    if origin_type is Union:
        return any(match_type(param_value, arg_type) for arg_type in get_args(param_type))
    return False


def match_type(param_value, param_type):
    """匹配具体类型的参数，包括 Optional 和 Union 类型。"""
    if isinstance(param_value, param_type):
        print(f":::{param_value=} is {param_type}")
        return True
    if match_optional_type(param_value, param_type):
        print(f":::{param_value=} is optional {param_type}")
        return True
    if match_union_type(param_value, param_type):
        print(f":::{param_value=} is union {param_type}")
        return True
    print(f":::{param_value=} is not {param_type}")
    return False


def is_optional_type(param_type):
    """检查是否为 Optional 类型。"""
    return get_origin(param_type) is Union and type(None) in get_args(param_type)


def resolve_kwargs(kwargs, annotations):
    """解析 kwargs 并删除已匹配的参数和注解。"""
    to_delete = [key for key, value in kwargs.items() if key in annotations and match_type(value, annotations[key])]

    for key in to_delete:
        del kwargs[key]
        del annotations[key]

    if "kwargs" in annotations:
        del annotations["kwargs"]
        kwargs.clear()


def resolve_args(args, annotations):
    """解析 args 并删除已匹配的参数和注解。"""
    to_delete = [i for i, arg in enumerate(args) if i < len(annotations) and match_type(arg, annotations[i])]

    for idx in sorted(to_delete, reverse=True):
        del args[idx]
        del annotations[idx]


def get_param_order(func):
    """获取函数的参数顺序。"""
    sig = inspect.signature(func)
    return list(sig.parameters.keys())


def route(**proposed_annotations):
    """方法调度器，根据给定的参数注解进行方法分发。"""
    if "routed_funcs" not in route.__dict__:
        route.__dict__["routed_funcs"] = defaultdict(list)

    def decorator(func):
        proposed_anns = {k: proposed_annotations.get(k, Optional[object]) for k in get_param_order(func)}
        func_full_name = get_full_method_name(func)
        route.__dict__["routed_funcs"][func_full_name].append([proposed_anns, func])

        def wrapper(*args, **kwargs):
            print(f"wrapper({args}, {kwargs})")
            record_ann_funcs = route.__dict__["routed_funcs"][func_full_name]

            for record_ann, record_func in record_ann_funcs:
                copy_record_ann = record_ann.copy()
                copy_args = list(args)
                copy_kwargs = kwargs.copy()

                resolve_kwargs(copy_kwargs, copy_record_ann)
                if len(copy_kwargs) > len(copy_record_ann):
                    print("传入参数比定义的多，跳过此函数")
                    continue

                if len(copy_kwargs) <= len(copy_record_ann):
                    if "args" in copy_record_ann:
                        print("匹配到 args 参数，直接调用函数")
                        return record_func(*args, **kwargs)

                    copy_args.extend(copy_kwargs.values())
                    copy_record_args = list(copy_record_ann.values())
                    resolve_args(copy_args, copy_record_args)

                    copy_record_args = [x for x in copy_record_args if not is_optional_type(x)]
                    if len(copy_args) > len(copy_record_args):
                        print("传入参数比定义的多，跳过此函数")
                        continue

                    if not copy_args and not copy_record_args:
                        print("完全匹配，执行函数")
                        return record_func(*args, **kwargs)

            available_annotations = '), ('.join(
                [', '.join([f"{k}:{v}" for k, v in a.items()]) for a, _ in record_ann_funcs])
            raise TypeError(f"Invalid arguments for {func.__name__}({args}, {kwargs}), \n"
                            f"available annotations: ({available_annotations})")

        return wrapper

    return decorator
