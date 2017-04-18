import numpy

from chainer import cuda
from chainer import function
from chainer.utils import type_check

if cuda.cudnn_enabled:
    cudnn = cuda.cudnn
    libcudnn = cudnn.cudnn
    _cudnn_version = libcudnn.getVersion()
    _algorithm = libcudnn.CUDNN_SOFTMAX_ACCURATE
    _mode = libcudnn.CUDNN_SOFTMAX_MODE_CHANNEL


class Softmax(function.Function):

    """Softmax activation function."""

    def __init__(self, use_cudnn=True, axis=1):
        self.use_cudnn = use_cudnn
        self.axis = axis

    def check_type_forward(self, in_types):
        type_check.expect(in_types.size() == 1)
        x_type, = in_types

        type_check.expect(
            x_type.dtype.kind == 'f',
            x_type.ndim > 1,
            self.axis < x_type.ndim
        )

    def forward(self, x):
        xp = cuda.get_array_module(*x)
        if (xp != numpy and cuda.cudnn_enabled and self.use_cudnn and
                (_cudnn_version >= 3000 or x[0].dtype != numpy.float16)):
            oz_dtype = 'd' if x[0].dtype == 'd' else 'f'
            one = numpy.array(1, dtype=oz_dtype).ctypes
            zero = numpy.array(0, dtype=oz_dtype).ctypes
            handle = cudnn.get_handle()
            x_tensor4d = x[0].reshape(self._get_tensor4d_shape(x[0].shape))
            desc = cudnn.create_tensor_descriptor(x_tensor4d)
            self.y = xp.empty_like(x[0])
            libcudnn.softmaxForward(
                handle, _algorithm, _mode, one.data, desc.value,
                x_tensor4d.data.ptr, zero.data, desc.value,
                self.y.data.ptr)
        else:
            self.y = x[0] - x[0].max(axis=self.axis, keepdims=True)
            xp.exp(self.y, out=self.y)
            self.y /= self.y.sum(axis=self.axis, keepdims=True)

        return self.y,

    def backward(self, x, gy):
        xp = cuda.get_array_module(*x)
        if (xp != numpy and cuda.cudnn_enabled and self.use_cudnn and
                (_cudnn_version >= 3000 or x[0].dtype != numpy.float16)):
            oz_dtype = 'd' if x[0].dtype == 'd' else 'f'
            one = numpy.array(1, dtype=oz_dtype).ctypes
            zero = numpy.array(0, dtype=oz_dtype).ctypes
            handle = cudnn.get_handle()
            gx = xp.empty_like(x[0])
            gx_tensor4d = gx.reshape(self._get_tensor4d_shape(gx.shape))
            desc = cudnn.create_tensor_descriptor(gx_tensor4d)
            libcudnn.softmaxBackward(
                handle, _algorithm, _mode, one.data, desc.value,
                self.y.data.ptr, desc.value, gy[0].data.ptr, zero.data,
                desc.value, gx.data.ptr)
        else:
            gx = self.y * gy[0]
            sumdx = gx.sum(axis=self.axis, keepdims=True)
            gx -= self.y * sumdx

        return gx,

    def _get_tensor4d_shape(self, shape):
        left_shape = numpy.prod(shape[slice(0, self.axis)], dtype=numpy.int)
        center_shape = shape[self.axis]
        right_shape = numpy.prod(
            shape[slice(self.axis + 1, len(shape))], dtype=numpy.int)
        return left_shape, center_shape, right_shape, 1


def softmax(x, use_cudnn=True, axis=1):
    """Softmax function.

    This function computes its softmax along an axis. Let
    :math:`x = (x_1, x_2, \\dots, x_d)^{\\top}` be the d dimensional index
    array and :math:`f(x)` be the d dimensional input array. For each index
    :math:`x` of the input array :math:`f(x)`, it computes the probability
    :math:`p(x)` defined as
    :math:`p(x) = {\\exp(f(x)) \\over \\sum_{x_2} \\exp(f(x))}`.
>>>>>>> master
    """Channel-wise softmax function.

    This function computes its softmax along the second axis. Let
    :math:`x=(x_1, x_2, \\dots, x_D)^{\\top}` be the D dimensional input
    array.
    For each input array :math:`x`, it computes the function :math:`f(x)`
    defined as :math:`f(x)={\\exp(x) \\over \\sum_{x_d} \\exp(x_d)}`.

    Args:
        x (:class:`~chainer.Variable` or :class:`numpy.ndarray` or \
        :class:`cupy.ndarray`):
            Input variable.
            A :math:`n`-dimensional (:math:`n \\geq 2`) float array.
        use_cudnn (bool): If ``True`` and cuDNN is enabled, then this function
            uses cuDNN as the core implementation.
        axis: The axis along which the softmax is to be computed.

    Returns:
        ~chainer.Variable: Output variable.
        A :math:`n`-dimensional (:math:`n \\geq 2`) float array, which is the
        same shape with x.

    .. admonition:: Example

        >>> x = np.array([[0, 1, 2], [0, 2, 4]], 'f')
        >>> x
        array([[ 0.,  1.,  2.],
               [ 0.,  2.,  4.]], dtype=float32)
        >>> y = F.softmax(x)
        >>> y.data
        array([[ 0.09003057,  0.24472848,  0.66524094],
               [ 0.01587624,  0.11731043,  0.86681336]], dtype=float32)
        >>> F.sum(y, axis=1).data
        array([ 1.,  1.], dtype=float32)

    """
    return Softmax(use_cudnn=use_cudnn, axis=axis)(x)
