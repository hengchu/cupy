import unittest

import numpy

import cupy
from cupy import cuda
from cupy import testing
from cupy.testing import condition


@unittest.skipUnless(
    cuda.cusolver_enabled, 'Only cusolver in CUDA 8.0 is supported')
@testing.gpu
@testing.fix_random()
class TestSolve(unittest.TestCase):

    @testing.for_dtypes('fdFD')
    # TODO(kataoka): Fix contiguity
    @testing.numpy_cupy_allclose(atol=1e-3, contiguous_check=False)
    def check_x(self, a_shape, b_shape, xp, dtype):
        a = testing.shaped_random(a_shape, xp, dtype=dtype, seed=0)
        b = testing.shaped_random(b_shape, xp, dtype=dtype, seed=1)
        a_copy = a.copy()
        b_copy = b.copy()
        result = xp.linalg.solve(a, b)
        cupy.testing.assert_array_equal(a_copy, a)
        cupy.testing.assert_array_equal(b_copy, b)
        return result

    def test_solve(self):
        self.check_x((4, 4), (4,))
        self.check_x((5, 5), (5, 2))
        self.check_x((2, 4, 4), (2, 4,))
        self.check_x((2, 5, 5), (2, 5, 2))
        self.check_x((2, 3, 2, 2), (2, 3, 2,))
        self.check_x((2, 3, 3, 3), (2, 3, 3, 2))

    @testing.numpy_cupy_raises()
    def check_shape(self, a_shape, b_shape, xp):
        a = xp.random.rand(*a_shape)
        b = xp.random.rand(*b_shape)
        xp.linalg.solve(a, b)

    def test_invalid_shape(self):
        self.check_shape((2, 3), (4,))
        self.check_shape((3, 3), (2,))
        self.check_shape((3, 3), (2, 2))
        self.check_shape((3, 3, 4), (3,))

    @testing.with_requires('numpy>=1.10')
    def test_invalid_shape2(self):
        # numpy 1.9 does not raise an error for this type of inputs
        self.check_shape((2, 3, 3), (3,))


@testing.parameterize(*testing.product({
    'a_shape': [(2, 3, 6), (3, 4, 4, 3)],
    'dtype': [numpy.float32, numpy.float64],
    'axes': [None, (0, 2)],
}))
@testing.fix_random()
@testing.gpu
@unittest.skipUnless(
    cuda.cusolver_enabled, 'Only cusolver in CUDA 8.0 is supported')
class TestTensorSolve(unittest.TestCase):

    def setUp(self):
        self.a = numpy.random.randint(
            0, 10, size=self.a_shape).astype(self.dtype)
        self.b = numpy.random.randint(
            0, 10, size=self.a_shape[:2]).astype(self.dtype)

    @testing.numpy_cupy_allclose(atol=0.02)
    def test_tensorsolve(self, xp):
        a = xp.array(self.a)
        b = xp.array(self.b)
        return xp.linalg.tensorsolve(a, b, axes=self.axes)


@unittest.skipUnless(
    cuda.cusolver_enabled, 'Only cusolver in CUDA 8.0 is supported')
@testing.gpu
class TestInv(unittest.TestCase):

    @testing.for_float_dtypes(no_float16=True)
    @condition.retry(10)
    def check_x(self, a_shape, dtype):
        a_cpu = numpy.random.randint(0, 10, size=a_shape).astype(dtype)
        a_gpu = cupy.asarray(a_cpu)
        a_gpu_copy = a_gpu.copy()
        result_cpu = numpy.linalg.inv(a_cpu)
        result_gpu = cupy.linalg.inv(a_gpu)
        self.assertEqual(result_cpu.dtype, result_gpu.dtype)
        cupy.testing.assert_allclose(result_cpu, result_gpu, atol=1e-3)
        cupy.testing.assert_array_equal(a_gpu_copy, a_gpu)

    def check_shape(self, a_shape):
        a = cupy.random.rand(*a_shape)
        with self.assertRaises(numpy.linalg.LinAlgError):
            cupy.linalg.inv(a)

    def test_inv(self):
        self.check_x((3, 3))
        self.check_x((4, 4))
        self.check_x((5, 5))

    def test_invalid_shape(self):
        self.check_shape((2, 3))
        self.check_shape((4, 1))


@unittest.skipUnless(
    cuda.cusolver_enabled, 'Only cusolver in CUDA 8.0 is supported')
@testing.gpu
class TestPinv(unittest.TestCase):

    @testing.for_float_dtypes(no_float16=True)
    @condition.retry(10)
    def check_x(self, a_shape, rcond, dtype):
        a_cpu = numpy.random.randint(0, 10, size=a_shape).astype(dtype)
        a_gpu = cupy.asarray(a_cpu)
        a_gpu_copy = a_gpu.copy()
        result_cpu = numpy.linalg.pinv(a_cpu, rcond=rcond)
        result_gpu = cupy.linalg.pinv(a_gpu, rcond=rcond)

        self.assertEqual(result_cpu.dtype, result_gpu.dtype)
        cupy.testing.assert_allclose(result_cpu, result_gpu, atol=1e-3)
        cupy.testing.assert_array_equal(a_gpu_copy, a_gpu)

    def check_shape(self, a_shape, rcond):
        a = cupy.random.rand(*a_shape)
        with self.assertRaises(numpy.linalg.LinAlgError):
            cupy.linalg.pinv(a)

    def test_pinv(self):
        self.check_x((3, 3), rcond=1e-15)
        self.check_x((2, 4), rcond=1e-15)
        self.check_x((3, 2), rcond=1e-15)

        self.check_x((4, 4), rcond=0.3)
        self.check_x((2, 5), rcond=0.5)
        self.check_x((5, 3), rcond=0.6)

    def test_invalid_shape(self):
        self.check_shape((2, 3, 4), rcond=1e-15)
        self.check_shape((2, 3, 4), rcond=0.5)
        self.check_shape((4, 3, 2, 1), rcond=1e-14)
        self.check_shape((4, 3, 2, 1), rcond=0.1)


@unittest.skipUnless(
    cuda.cusolver_enabled, 'Only cusolver in CUDA 8.0 is supported')
@testing.gpu
class TestLstsq(unittest.TestCase):

    @testing.for_float_dtypes(no_float16=True)
    @condition.retry(10)
    def check_lstsq_solution(self, a_shape, b_shape, rcond, dtype):
        a_cpu = numpy.random.randint(0, 10, size=a_shape).astype(dtype)
        b_cpu = numpy.random.randint(0, 10, size=b_shape).astype(dtype)
        a_gpu = cupy.asarray(a_cpu)
        b_gpu = cupy.asarray(b_cpu)
        a_gpu_copy = a_gpu.copy()
        b_gpu_copy = b_gpu.copy()
        x_cpu, resids_cpu, rank_cpu, s_cpu = numpy.linalg.lstsq(a_cpu,
                                                                b_cpu,
                                                                rcond=rcond)
        x_gpu, resids_gpu, rank_gpu, s_gpu = cupy.linalg.lstsq(a_gpu,
                                                               b_gpu,
                                                               rcond=rcond)
        self.assertEqual(x_cpu.dtype, x_gpu.dtype)
        # check the least squares solutions are close
        cupy.testing.assert_allclose(x_cpu, x_gpu, atol=1e-3)
        cupy.testing.assert_allclose(resids_cpu, resids_gpu, atol=1e-3)
        self.assertEqual(rank_cpu, rank_gpu)
        cupy.testing.assert_allclose(s_cpu, s_gpu, atol=1e-3)
        # check that lstsq did not modify arrays
        cupy.testing.assert_array_equal(a_gpu_copy, a_gpu)
        cupy.testing.assert_array_equal(b_gpu_copy, b_gpu)

    def check_invalid_shapes(self, a_shape, b_shape):
        a = cupy.random.rand(*a_shape)
        b = cupy.random.rand(*b_shape)
        with self.assertRaises(numpy.linalg.LinAlgError):
            cupy.linalg.lstsq(a, b)

    def test_lstsq_solutions(self):
        # Test skinny
        self.check_lstsq_solution((10, 3), (10, ), rcond=1e-15)
        self.check_lstsq_solution((10, 3), (10, 2), rcond=1e-15)
        # Test square
        self.check_lstsq_solution((4, 4), (4, ), rcond=1e-15)
        self.check_lstsq_solution((4, 4), (4, 2), rcond=1e-15)
        # Test more unknowns than data
        self.check_lstsq_solution((3, 10), (3, ), rcond=1e-15)
        self.check_lstsq_solution((3, 10), (3, 3), rcond=1e-15)
        # Test large rcond
        self.check_lstsq_solution((4, 4), (4,), rcond=0.3)
        self.check_lstsq_solution((2, 5), (2,), rcond=0.5)
        self.check_lstsq_solution((5, 3), (5,), rcond=0.6)

    def test_invalid_shapes(self):
        self.check_invalid_shapes((4, 3), (3, ))
        self.check_invalid_shapes((3, 3, 3), (2, 2))
        self.check_invalid_shapes((3, 3, 3), (3, 3))
        self.check_invalid_shapes((3, 3), (3, 3, 3))
        self.check_invalid_shapes((2, 2), (10, ))
        self.check_invalid_shapes((3, 3), (2, 2))
        self.check_invalid_shapes((4, 3), (10, 3, 3))


@unittest.skipUnless(
    cuda.cusolver_enabled, 'Only cusolver in CUDA 8.0 is supported')
@testing.gpu
class TestTensorInv(unittest.TestCase):

    @testing.for_float_dtypes(no_float16=True)
    @condition.retry(10)
    def check_x(self, a_shape, ind, dtype):
        a_cpu = numpy.random.randint(0, 10, size=a_shape).astype(dtype)
        a_gpu = cupy.asarray(a_cpu)
        a_gpu_copy = a_gpu.copy()
        result_cpu = numpy.linalg.tensorinv(a_cpu, ind=ind)
        result_gpu = cupy.linalg.tensorinv(a_gpu, ind=ind)
        self.assertEqual(result_cpu.dtype, result_gpu.dtype)
        cupy.testing.assert_allclose(result_cpu, result_gpu, atol=1e-3)
        cupy.testing.assert_array_equal(a_gpu_copy, a_gpu)

    def check_shape(self, a_shape, ind):
        a = cupy.random.rand(*a_shape)
        with self.assertRaises(numpy.linalg.LinAlgError):
            cupy.linalg.tensorinv(a, ind=ind)

    def check_ind(self, a_shape, ind):
        a = cupy.random.rand(*a_shape)
        with self.assertRaises(ValueError):
            cupy.linalg.tensorinv(a, ind=ind)

    def test_tensorinv(self):
        self.check_x((12, 3, 4), ind=1)
        self.check_x((3, 8, 24), ind=2)
        self.check_x((18, 3, 3, 2), ind=1)
        self.check_x((1, 4, 2, 2), ind=2)
        self.check_x((2, 3, 5, 30), ind=3)
        self.check_x((24, 2, 2, 3, 2), ind=1)
        self.check_x((3, 4, 2, 3, 2), ind=2)
        self.check_x((1, 2, 3, 2, 3), ind=3)
        self.check_x((3, 2, 1, 2, 12), ind=4)

    def test_invalid_shape(self):
        self.check_shape((2, 3, 4), ind=1)
        self.check_shape((1, 2, 3, 4), ind=3)

    def test_invalid_index(self):
        self.check_ind((12, 3, 4), ind=-1)
        self.check_ind((18, 3, 3, 2), ind=0)
