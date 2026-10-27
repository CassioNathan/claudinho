# Claudinho: o Piper traz esse pedaço em Cython (precisa de compilador C++). Mesma conta, compilada pelo numba.
import numba


@numba.jit(nopython=True, nogil=True)
def _um(path, value, t_y, t_x, max_neg_val=-1e9):
    index = t_x - 1
    for y in range(t_y):
        for x in range(max(0, t_x + y - t_y), min(t_x, y + 1)):
            v_cur = max_neg_val if x == y else value[y - 1, x]
            if x == 0:
                v_prev = 0.0 if y == 0 else max_neg_val
            else:
                v_prev = value[y - 1, x - 1]
            value[y, x] += max(v_prev, v_cur)
    for y in range(t_y - 1, -1, -1):
        path[y, index] = 1
        if index != 0 and (index == y or value[y - 1, index] < value[y - 1, index - 1]):
            index = index - 1


@numba.jit(nopython=True, nogil=True, parallel=True)
def maximum_path_c(paths, values, t_ys, t_xs):
    for i in numba.prange(paths.shape[0]):
        _um(paths[i], values[i], t_ys[i], t_xs[i])
