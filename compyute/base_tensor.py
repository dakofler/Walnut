"""Tensor module"""

from __future__ import annotations

from types import ModuleType
from typing import Any, Optional, TypeAlias

import numpy

from .dtypes import Dtype, _DtypeLike, _ScalarLike, get_string_from_dtype
from .engine import (
    Device,
    _ArrayLike,
    _check_device_availability,
    _DeviceLike,
    cupy_to_numpy,
    get_array_string,
    get_engine,
    infer_device,
    numpy_to_cupy,
)

__all__ = ["tensor", "Tensor"]

_ShapeLike: TypeAlias = tuple[int, ...]
_AxisLike: TypeAlias = int | tuple[int, ...]


class ShapeError(Exception):
    """Incompatible tensor shapes."""


def tensor(
    data: _ArrayLike | _ScalarLike,
    device: Optional[_DeviceLike] = None,
    dtype: Optional[_DtypeLike] = None,
    copy: bool = False,
    requires_grad: bool = True,
) -> Tensor:
    """Creates a tensor object.

    Parameters
    ----------
    data : _ArrayLike | _ScalarLike
        Data to initialize the tensor.
    device : _DeviceLike, optional
        Device the tensor should be stored on. If None it is inferred from the data.
    dtype : _DtypeLike, optional
        Data type of tensor data. If None it is inferred from the data.
    copy: bool, optional
        If true, the data object is copied (may impact performance), by default False.
    requires_grad: bool, optional
        Whether the tensor requires gradients, by default True.
    """
    device = infer_device(data) if device is None else device
    dtype = get_string_from_dtype(dtype)
    data = get_engine(device).array(data, copy=copy, dtype=dtype)
    return Tensor(data, requires_grad)


class Tensor:
    """Tensor object."""

    def __init__(
        self,
        data: _ArrayLike,
        requires_grad: bool = True,
    ) -> None:
        """Tensor object.

        Parameters
        ----------
        data : _ArrayLike
            Data to initialize the tensor.
        requires_grad: bool, optional
            Whether the tensor requires gradients, by default True.
        """
        self.data = data
        self.requires_grad = requires_grad
        self.grad: Optional[Tensor] = None
        self._iterator: int = 0

    # ----------------------------------------------------------------------------------------------
    # PROPERTIES
    # ----------------------------------------------------------------------------------------------

    @staticmethod
    def as_tensor(value: _ArrayLike | _ScalarLike) -> Tensor:
        """Converts a value to a tensor."""
        if isinstance(value, _ArrayLike):
            return Tensor(value)
        return tensor(value)

    @staticmethod
    def as_array(value: Any) -> _ArrayLike:
        """Converts a value to an array."""
        if isinstance(value, Tensor):
            return value.data
        return value

    @property
    def data(self) -> _ArrayLike:
        """Tensor data."""
        return self._data

    @data.setter
    def data(self, value: _ArrayLike) -> None:
        if not isinstance(value, _ArrayLike):
            raise ValueError(
                f"Invalid data type {type(value)}. Use compyute.tensor to initialize tensors."
            )
        self._data = value

    @property
    def _engine(self) -> ModuleType:
        return get_engine(self.device)

    @property
    def device(self) -> Device:
        """Device the tensor is stored on."""
        return infer_device(self._data)

    def to_device(self, device: _DeviceLike) -> None:
        """Moves the tensor to a specified device."""
        device = Device(device)
        if self.device == device:
            return
        _check_device_availability(device)

        if device == Device.CUDA:
            self._data = numpy_to_cupy(self._data)
        else:
            self._data = cupy_to_numpy(self._data)

        if self.grad is not None:
            self.grad.to_device(device)

    @property
    def dtype(self) -> Dtype:
        """Tensor data type."""
        return Dtype(str(self._data.dtype))

    @property
    def ndim(self) -> int:
        """Number of tensor dimensions."""
        return self._data.ndim

    @property
    def size(self) -> int:
        """Tensor size."""
        return self._data.size

    @property
    def shape(self) -> _ShapeLike:
        """Tensor shape."""
        return self._data.shape

    @property
    def strides(self) -> tuple[int, ...]:
        """Tensor strides."""
        return self._data.strides

    @property
    def T(self) -> Tensor:
        """Transposed tensor."""
        return Tensor(self._engine.moveaxis(self._data, -2, -1))

    # ----------------------------------------------------------------------------------------------
    # MAGIC METHODS
    # ----------------------------------------------------------------------------------------------

    def __repr__(self) -> str:
        array_string = get_array_string(self.cpu().data)
        return f"Tensor({array_string})"

    def __getitem__(self, key: Any) -> Tensor:
        i = tuple(self.as_array(j) for j in key) if isinstance(key, tuple) else self.as_array(key)
        return self.as_tensor(self._data[i])

    def __setitem__(self, key: Any, value: Tensor | _ScalarLike) -> None:
        self._data[self.as_array(key)] = self.as_array(value)

    def __iter__(self) -> Tensor:
        self._iterator = 0
        return self

    def __next__(self) -> Tensor | _ScalarLike:
        if self._iterator < self.shape[0]:
            data = self[self._iterator]
            self._iterator += 1
            return data
        raise StopIteration

    def __add__(self, other: Tensor | _ScalarLike) -> Tensor:
        return self.as_tensor(self._data + self.as_array(other))

    def __radd__(self, other: _ScalarLike) -> Tensor:
        other = 0.0 if other is None else other  # for gradient accumulation
        return self + other

    def __mul__(self, other: Tensor | _ScalarLike) -> Tensor:
        return self.as_tensor(self._data * self.as_array(other))

    def __rmul__(self, other: _ScalarLike) -> Tensor:
        return self * other

    def __pow__(self, other: Tensor | _ScalarLike) -> Tensor:
        return self.as_tensor(self._data ** self.as_array(other))

    def __rpow__(self, other: _ScalarLike) -> Tensor:
        return tensor(other, self.device) ** self

    def __neg__(self) -> Tensor:
        return self * -1

    def __sub__(self, other: Tensor | _ScalarLike) -> Tensor:
        return self.as_tensor(self._data - self.as_array(other))

    def __rsub__(self, other: _ScalarLike) -> Tensor:
        return -self + other

    def __truediv__(self, other: Tensor | _ScalarLike) -> Tensor:
        return self.as_tensor(self._data / self.as_array(other))

    def __rtruediv__(self, other: _ScalarLike) -> Tensor:
        return self**-1 * other

    def __floordiv__(self, other: Tensor | _ScalarLike) -> Tensor:
        return self.as_tensor(self._data // self.as_array(other))

    def __rfloordiv__(self, other: _ScalarLike) -> Tensor:
        return (other // self).as_type(self.dtype)

    def __mod__(self, other: int) -> Tensor:
        return self.as_tensor(self._data % other)

    def __matmul__(self, other: Tensor) -> Tensor:
        return self.as_tensor(self._data @ other.data)

    def __lt__(self, other: Tensor | _ScalarLike) -> Tensor:
        return self.as_tensor(self._data < self.as_array(other))

    def __gt__(self, other: Tensor | _ScalarLike) -> Tensor:
        return self.as_tensor(self._data > self.as_array(other))

    def __le__(self, other: Tensor | _ScalarLike) -> Tensor:
        return self.as_tensor(self._data <= self.as_array(other))

    def __ge__(self, other: Tensor | _ScalarLike) -> Tensor:
        return self.as_tensor(self._data >= self.as_array(other))

    def __eq__(self, other: Tensor | _ScalarLike) -> Tensor:
        return self.as_tensor(self._data == self.as_array(other))

    def __ne__(self, other: Tensor | _ScalarLike) -> Tensor:
        return self.as_tensor(self._data != self.as_array(other))

    def __iadd__(self, other: Tensor | _ScalarLike) -> Tensor:
        self._data += self.as_array(other)
        return self

    def __isub__(self, other: Tensor | _ScalarLike) -> Tensor:
        self._data -= self.as_array(other)
        return self

    def __imul__(self, other: Tensor | _ScalarLike) -> Tensor:
        self._data *= self.as_array(other)
        return self

    def __idiv__(self, other: Tensor | _ScalarLike) -> Tensor:
        self._data /= self.as_array(other)
        return self

    def __ifloordiv__(self, other: Tensor | _ScalarLike) -> Tensor:
        self._data //= self.as_array(other)
        return self

    def __imod__(self, other: Tensor | _ScalarLike) -> Tensor:
        self._data %= self.as_array(other)
        return self

    def __ipow__(self, other: Tensor | _ScalarLike) -> Tensor:
        self._data **= self.as_array(other)
        return self

    def __len__(self) -> int:
        return self.shape[0]

    def __hash__(self):
        return id(self)

    def __array__(self, dtype=None, copy=None):
        return self.to_numpy()

    # ----------------------------------------------------------------------------------------------
    # DTYPE CONVERSIONS
    # ----------------------------------------------------------------------------------------------

    def as_type(self, dtype: _DtypeLike) -> Tensor:
        """Returns a copy of the tensor with parsed values.

        Parameters
        ----------
        dtype : _DtypeLike
            Datatype to convert the tensor to.

        Returns
        -------
        Tensor
            Tensor of dtype.
        """
        return tensor(self._data, self.device, dtype=dtype)

    def int(self) -> Tensor:
        """Returns a copy of the tensor with int values."""
        return self.as_type(Dtype.INT32)

    def long(self) -> Tensor:
        """Returns a copy of the tensor with long values."""
        return self.as_type(Dtype.INT16)

    def half(self) -> Tensor:
        """Returns a copy of the tensor with half precision values."""
        return self.as_type(Dtype.FLOAT16)

    def float(self) -> Tensor:
        """Returns a copy of the tensor with float values."""
        return self.as_type(Dtype.FLOAT32)

    def double(self) -> Tensor:
        """Returns a copy of the tensor with double precision values."""
        return self.as_type(Dtype.FLOAT64)

    def complex(self) -> Tensor:
        """Returns a copy of the tensor with complex values."""
        return self.as_type(Dtype.COMPLEX64)

    def to_numpy(self) -> numpy.ndarray:
        """Returns the tensor data as a NumPy array."""
        return self.cpu().data

    # ----------------------------------------------------------------------------------------------
    # MEMORY/DEVICE METHODS
    # ----------------------------------------------------------------------------------------------

    def copy(self) -> Tensor:
        """Returns a copy of the tensor."""
        t = Tensor(self._data.copy(), requires_grad=self.requires_grad)
        t.grad = None if self.grad is None else self.grad.copy()
        return t

    def item(self) -> _ScalarLike:
        """Returns the scalar value of the tensor data."""
        return self._data.item()

    def cpu(self):
        """Returns a copy of the tensor on the cpu."""
        if self.device == Device.CPU:
            return self

        new_tensor = self.copy()
        new_tensor.to_device(Device.CPU)
        return new_tensor

    def cuda(self):
        """Returns a copy of the tensor on the gpu."""
        if self.device == Device.CUDA:
            return self

        new_tensor = self.copy()
        new_tensor.to_device(Device.CUDA)
        return new_tensor
