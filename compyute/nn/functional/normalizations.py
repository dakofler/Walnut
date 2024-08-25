"""Neural network normalization functions."""

from ...tensor_ops.reshaping import insert_dim, squeeze
from ...tensor_ops.transforming import mean as cpmean
from ...tensor_ops.transforming import sqrt
from ...tensor_ops.transforming import sum as cpsum
from ...tensor_ops.transforming import var as cpvar
from ...tensors import Tensor
from .functions import Function, FunctionCache, PseudoCache

__all__ = ["batchnorm1d", "batchnorm2d", "layernorm", "rmsnorm"]


class FBatchNorm1D(Function):
    """Performs 1D batch normalization on a tensor."""

    @staticmethod
    def forward(
        cache: FunctionCache,
        x: Tensor,
        rmean: Tensor,
        rvar: Tensor,
        w: Tensor,
        b: Tensor,
        m: float,
        eps: float,
        training: bool,
    ) -> tuple[Tensor, Tensor, Tensor]:
        x_is_2d = x.n_axes == 2
        axes = 0 if x_is_2d else (0, 2)

        if training:
            # compute mean and variance from x
            mean = cpmean(x, axis=axes, keepdims=True)
            var = cpvar(x, axis=axes, keepdims=True)
            inv_std = 1 / sqrt(var + eps)
            x_norm = (x - mean) * inv_std

            # keep running stats
            rmean = rmean * (1 - m) + squeeze(mean) * m
            rvar = rvar * (1 - m) + cpvar(x, axis=axes, ddof=1) * m
        else:
            # use running mean and variance
            rvar_ = rvar if x_is_2d else insert_dim(rvar, -1)
            rmean_ = rmean if x_is_2d else insert_dim(rmean, -1)
            inv_std = 1 / sqrt(rvar_ + eps)
            x_norm = (x - rmean_) * inv_std

        w = w if x_is_2d else insert_dim(w, -1)
        b = b if x_is_2d else insert_dim(b, -1)
        y = w * x_norm + b

        cache.bn1d_w, cache.bn1d_inv_std, cache.bn1d_x_norm = w, inv_std, x_norm
        return y, rmean, rvar

    @staticmethod
    def backward(cache: FunctionCache, dy: Tensor) -> tuple[Tensor, Tensor, Tensor]:
        w, inv_std, x_norm = cache.bn1d_w, cache.bn1d_inv_std, cache.bn1d_x_norm
        axes = 0 if dy.n_axes == 2 else (0, 2)

        # input grads
        n = float(dy.size / dy.shape[1])
        dy_sum = cpsum(dy, axis=axes, keepdims=True)
        dy_x_norm_sum = cpsum(dy * x_norm, axis=axes, keepdims=True)
        dx = w * inv_std / n * (n * dy - dy_sum - x_norm * dy_x_norm_sum)

        # gamma grads
        dw = squeeze(dy_x_norm_sum)

        # beta grads
        db = squeeze(dy_sum)

        return dx, dw, db


def batchnorm1d(
    x: Tensor,
    rmean: Tensor,
    rvar: Tensor,
    w: Tensor,
    b: Tensor,
    m: float = 0.1,
    eps: float = 1e-5,
    training: bool = False,
) -> tuple[Tensor, Tensor, Tensor]:
    """Performs 1D batch normalization on a tensor.

    Parameters
    ----------
    x : Tensor
        Input tensor.
    rmean : Tensor
        Running mean tensor.
    rvar : Tensor
        Running variance tensor.
    w : Tensor
        Weight tensor for scaling the distribution.
    b : Tensor
        Bias tensor for shifting the distribution.
    m : float, optional
        Momentum used for running mean and variance computation. Defaults to ``0.1``.
    eps : float, optional
        Constant for numerical stability. Defaults to ``1e-5``.
    training : bool, optional
        Whether to perform calculations in training mode. Defaults to ``False``.

    Returns
    -------
    Tensor
        Output tensor.
    Tensor
        New running mean.
    Tensor
        New running variance.

    See Also
    ----------
    :class:`compyute.nn.BatchNorm1D`
    """
    return FBatchNorm1D.forward(PseudoCache(), x, rmean, rvar, w, b, m, eps, training)


class FBatchNorm2D(Function):
    """Performs 2D batch normalization on a tensor."""

    @staticmethod
    def forward(
        cache: FunctionCache,
        x: Tensor,
        rmean: Tensor,
        rvar: Tensor,
        w: Tensor,
        b: Tensor,
        m: float,
        eps: float,
        training: bool,
    ) -> tuple[Tensor, Tensor, Tensor]:
        axes = (0, 2, 3)

        if training:
            # compute mean and variance from x
            mean = cpmean(x, axis=axes, keepdims=True)
            var = cpvar(x, axis=axes, keepdims=True)
            inv_std = 1 / sqrt(var + eps)
            x_norm = (x - mean) * inv_std

            # keep running stats
            rmean = rmean * (1 - m) + squeeze(mean) * m
            rvar = rvar * (1 - m) + cpvar(x, axis=axes, ddof=1) * m
        else:
            # use running mean and variance
            inv_std = 1 / sqrt(rvar.to_shape((*rvar.shape, 1, 1)) + eps)
            x_norm = (x - rmean.to_shape((*rmean.shape, 1, 1))) * inv_std

        w = w.to_shape((*w.shape, 1, 1))
        b = b.to_shape((*b.shape, 1, 1))
        y = w * x_norm + b

        cache.bn2d_w, cache.bn2d_inv_std, cache.bn2d_x_norm = w, inv_std, x_norm
        return y, rmean, rvar

    @staticmethod
    def backward(cache: FunctionCache, dy: Tensor) -> tuple[Tensor, Tensor, Tensor]:
        w, inv_std, x_norm = cache.bn2d_w, cache.bn2d_inv_std, cache.bn2d_x_norm
        axes = (0, 2, 3)
        n = float(dy.size / dy.shape[1])

        # input grads
        dy_sum = cpsum(dy, axis=axes, keepdims=True)
        dy_x_norm_sum = cpsum(dy * x_norm, axis=axes, keepdims=True)
        dx = w * inv_std / n * (n * dy - dy_sum - x_norm * dy_x_norm_sum)

        # gamma grads
        dw = squeeze(dy_x_norm_sum)

        # beta grads
        db = squeeze(dy_sum)

        return dx, dw, db


def batchnorm2d(
    x: Tensor,
    rmean: Tensor,
    rvar: Tensor,
    w: Tensor,
    b: Tensor,
    m: float = 0.1,
    eps: float = 1e-5,
    training: bool = False,
) -> tuple[Tensor, Tensor, Tensor]:
    """Performs 2D batch normalization on a tensor.

    Parameters
    ----------
    x : Tensor
        Input tensor.
    rmean : Tensor
        Running mean values.
    rvar : Tensor
        Running variance values.
    w : Tensor
        Weight tensor for scaling the distribution.
    b : Tensor
        Bias tensor for shifting the distribution.
    m : float, optional
        Momentum used for running mean and variance computation. Defaults to ``0.1``.
    eps : float, optional
        Constant for numerical stability. Defaults to ``1e-5``.
    training : bool, optional
        Whether to perform calculations in training mode. Defaults to ``False``.

    Returns
    -------
    Tensor
        Output tensor.
    Tensor
        New running mean.
    Tensor
        New running variance.

    See Also
    ----------
    :class:`compyute.nn.BatchNorm2D`
    """
    return FBatchNorm2D.forward(PseudoCache(), x, rmean, rvar, w, b, m, eps, training)


class FLayerNorm(Function):
    """Performs layer normalization on a tensor."""

    @staticmethod
    def forward(
        cache: FunctionCache, x: Tensor, w: Tensor, b: Tensor, eps: float
    ) -> Tensor:
        axes = tuple(-i - 1 for i in range(w.n_axes))

        inv_std = 1 / sqrt(cpvar(x, axis=axes, keepdims=True) + eps)
        x_norm = (x - cpmean(x, axis=axes, keepdims=True)) * inv_std
        y = w * x_norm + b

        cache.ln_w, cache.ln_inv_std, cache.ln_x_norm = w, inv_std, x_norm
        return y

    @staticmethod
    def backward(cache: FunctionCache, dy: Tensor) -> tuple[Tensor, Tensor, Tensor]:
        w, inv_std, x_norm = cache.ln_w, cache.ln_inv_std, cache.ln_x_norm
        axes = tuple(-i - 1 for i in range(w.n_axes))
        sum_axes = tuple(range(dy.n_axes - w.n_axes))

        # input grads
        dy_sum = cpsum(dy, axis=axes, keepdims=True)
        dy_x_std_sum = cpsum(dy * x_norm, axis=axes, keepdims=True)
        dx = w * inv_std / w.size * (w.size * dy - dy_sum - x_norm * dy_x_std_sum)

        # gamma grads
        dw = cpsum(dy * x_norm, axis=sum_axes)

        # beta grads
        db = cpsum(dy, axis=sum_axes)

        return dx, dw, db


def layernorm(x: Tensor, w: Tensor, b: Tensor, eps: float = 1e-5) -> Tensor:
    """Performs layer normalization on a tensor.

    Parameters
    ----------
    x : Tensor
        Input tensor.
    w : Tensor
        Weight tensor for scaling the distribution.
    b : Tensor
        Bias tensor for shifting the distribution.
    eps : float, optional
        Constant for numerical stability. Defaults to ``1e-5``.

    Returns
    -------
    Tensor
        Output tensor.

    See Also
    ----------
    :class:`compyute.nn.LayerNorm`
    """
    return FLayerNorm.forward(PseudoCache(), x, w, b, eps)


class FRMSNorm(Function):
    """Performs RMS normalization on a tensor."""

    @staticmethod
    def forward(cache: FunctionCache, x: Tensor, w: Tensor, eps: float) -> Tensor:
        axes = tuple(-i - 1 for i in range(w.n_axes))

        rms = sqrt(cpmean(x**2, axis=axes, keepdims=True) + eps)
        x_norm = x / rms
        y = w * x_norm

        cache.rms_x, cache.rms_w, cache.rms, cache.rms_x_norm = x, w, rms, x_norm
        return y

    @staticmethod
    def backward(cache: FunctionCache, dy: Tensor) -> tuple[Tensor, Tensor]:
        x, w, rms, x_norm = cache.rms_x, cache.rms_w, cache.rms, cache.rms_x_norm
        axes = tuple(-i - 1 for i in range(w.n_axes))
        sum_axes = tuple(range(x.n_axes - w.n_axes))

        # input grads
        dy_x_sum = cpsum(dy * x, axis=axes, keepdims=True)
        dx = w * (dy / rms - x * dy_x_sum / (w.size * rms**3))

        # gamma grads
        dw = cpsum(dy * x_norm, axis=sum_axes)

        return dx, dw


def rmsnorm(x: Tensor, w: Tensor, eps: float = 1e-5) -> Tensor:
    """Performs RMS normalization on a tensor.

    Parameters
    ----------
    x : Tensor
        Input tensor.
    w : Tensor
        Weight tensor for scaling the distribution.
    eps : float, optional
        Constant for numerical stability. Defaults to ``1e-5``.

    Returns
    -------
    Tensor
        Output tensor.

    See Also
    ----------
    :class:`compyute.nn.RMSNorm`
    """
    return FRMSNorm.forward(PseudoCache(), x, w, eps)
