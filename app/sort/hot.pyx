import math

cdef extern from "math.h":
    double log10(double)


cpdef double get_score(int s, long timestamp):
    order = log10(max(abs(s), 1))
    sign = 1 if s > 0 else -1 if s < 0 else 0
    seconds = timestamp - 1134028003
    return round(sign * order + seconds / 45000, 7)
