"""USD-backed OVStage-compatible shim used only on macOS."""
from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace

import numpy as np


class Scope:
    ALL = "ALL"


class AttributeSemantic:
    MATRIX = "MATRIX"


class PrimMode:
    UPSERT = "UPSERT"


class DLDataTypeCode:
    kDLFloat = "float"


class DLDataType:
    def __init__(self, code, bits, lanes):
        self.code, self.bits, self.lanes = code, bits, lanes


class _Immediate:
    def wait(self):
        return self


class _Tensor:
    def __init__(self, array):
        self.array = np.asarray(array)

    def __dlpack__(self, *args, **kwargs):
        return self.array.__dlpack__(*args, **kwargs)


def make_dltensor(array, dtype=None, shape=None):
    data = np.asarray(array)
    if shape is not None:
        data = data.reshape(tuple(shape) + data.shape[1:])
    return _Tensor(data)


class PathDictionary:
    def __init__(self, stage):
        self._stage = stage

    def intern_token(self, name):
        return str(name)

    @contextmanager
    def create_path_list_from_strings(self, paths):
        yield SimpleNamespace(paths=list(paths))


class Stage:
    def __init__(self, name):
        self.name = name
        self.usd = None
        self.xforms = {}
        self.ordinal = 0

    def destroy(self):
        self.usd = None
        self.xforms.clear()

    def advance_write_floor(self, ordinal, scope=None):
        self.ordinal = int(ordinal)
        return _Immediate()

    @contextmanager
    def query_from_path_list(self, path_list):
        yield SimpleNamespace(paths=list(path_list.paths))

    def write_attribute(self, query, token, ordinal=0, tensors=None, is_array=False,
                        semantic=None, prim_mode=None):
        del is_array, semantic, prim_mode
        if str(token) != "omni:xform":
            return _Immediate()
        data = getattr(tensors, "array", tensors)
        matrices = np.asarray(data, dtype=np.float64).reshape(len(query.paths), 4, 4)
        for path, matrix in zip(query.paths, matrices):
            self.xforms[str(path)] = np.array(matrix, copy=True)
        self.ordinal = int(ordinal)
        return _Immediate()


class population:
    @staticmethod
    def open_usd(stage, absolute_usd_path, ordinal=0):
        from pxr import Usd
        opened = Usd.Stage.Open(str(absolute_usd_path))
        if opened is None:
            raise OSError(f"Could not parse USD: {absolute_usd_path}")
        stage.usd = opened
        stage.xforms.clear()
        stage.ordinal = int(ordinal)
