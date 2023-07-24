from sage.all import *
import random
import matplotlib.pyplot as plt

"""
    Execution instructions:
    If you want to run the tests to get the plotted results, run:
    test_decoders(GF, K_LIST)
    There are some default values included for GF(7), GF(97), GF(929)
    Run the tests with them as 
    test_decoders(GF97, ks_for_gf97) for example
    
    There is documentation above each rs encoder/decoder method to explain the arguments 
"""


def rs_encoder(msg, n, gf):
    """
    Reed Solomon encoder
    ------------------------------------------------------
    Parameters:
    :param msg - message to be encoded, given as a list
    :param n   - length of the desired encrypted message (or degree of encrypted message polynomial)
    :param gf  - finite field over which to encode
    :return the encrypted polynomial of degree n - 1 generated by:
    1. Interpolating the given message polynomial msg with the values [0, ..., k - 1]
    2. Evaluating the interpolated polynomial at the first n values of the ring [0, ..., n]
    3. The return value is a galois polynomial with coefficients derived from the previous step
    """
    k = len(msg)
    alphas_k = list(range(k))

    ring = PolynomialRing(gf, 'x')
    # Compute the interpolation polynomial of ([ [0, coeff[0]], ..., [i, coeff[i]], ..., [k - 1, coeff[k - 1]])
    lp = ring.lagrange_polynomial(zip(alphas_k, msg))

    # Receive the codeword by evaluating the interpolation polynomial at the first n alphas of the finite field
    codeword = [lp(a) for a in list(range(n))]

    return ring(codeword)


def error_generator(codeword, num_of_errors, gf):
    """
    Error Generator
    ------------------------------------------------------
    Parameters:
    :param codeword      - encoded message
    :param num_of_errors - number of errors to be introduced
    :param gf            - finite field over which to introduce errors
    :return a tuple of the codeword with the errors and the number of errors introduced (codeword, error_num)
    """
    n = codeword.degree() + 1
    if num_of_errors > n:
        num_of_errors = n

    q = gf.characteristic()
    coeffs = codeword.list()

    indices_to_change = []
    while len(indices_to_change) < num_of_errors:
        index = random.randint(0, len(coeffs) - 1)
        if index not in indices_to_change:
            indices_to_change.append(index)

    for index in indices_to_change:
        current_coeff = coeffs[index]
        while true:
            random_value = random.randint(0, q)
            if index == len(coeffs) - 1 and random_value == 0:
                continue
            if random_value != current_coeff:
                coeffs[index] = random_value
                break

    new_codeword = PolynomialRing(gf, 'x')(coeffs)
    return new_codeword, num_of_errors


def rs_decoder(codeword, k, num_of_errors, gf):
    """
    Reed Solomon Unique Decoder
    ------------------------------------------------------
    This is my implementation of the Berlekamp-Welch unique decoder algorithm
    Parameters:
    :param codeword      - message to be decoded, given as a list
    :param k             - length of the original message
    :param num_of_errors - number of errors in the received codeword
    :param gf            - finite field over which to decode
    :return the original message polynomial of degree k - 1 generated by:
        1. Generate the linear equations necessary to calculate the locations of errors within the received codeword
        2. Row reduce the created matrix in order to calculate the error locator polynomial
        3. Locate the indices of the errors
        4. Interpolate a polynomial from the first n alphas of the field excluding the error indices
        5. Evaluate the interpolated polynomial at the first k alphas of the field to obtain the original message
        6. The return value is a galois polynomial with coefficients derived from the previous step

        or None if failed to decode
    """

    n = len(codeword)
    q = gf.characteristic()
    ring = PolynomialRing(gf, 'x')

    # Generate the linear equations to calculate the original message polynomial based on the Berlekamp-Welch algorithm

    # Calculate the result column of the linear equations
    result_column = [int((-1) * element * (alpha ** 2)) for alpha, element in enumerate(codeword)]

    # Calculate the linear equations coefficients
    equations = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if j == 0:
                equations[i][j] = int(codeword[i])
            elif j == 1:
                equations[i][j] = int((codeword[i] * i))
            elif j == 2:
                equations[i][j] = q - 1
            else:
                equations[i][j] = (q - ((i ** (j - 2)) % q)) % q

    # Solve equations*unknowns = result_column
    try:
        unknowns = Matrix(ring, equations).solve_right(vector(ring, result_column))
    except Exception:
        return None

    # Find the error locator polynomial

    # Use F to recalculate the correct encoded message without errors
    F = None

    error_coeffs = list(unknowns[:num_of_errors]) + [1]
    E = PolynomialRing(ring, 'x')(error_coeffs)

    q_coeffs = list(unknowns[num_of_errors:])
    Q = PolynomialRing(ring, 'x')(q_coeffs)

    if Q % E == 0:
        F = Q // E
    else:
        return None

    # Gather the locations of all the correct symbols so that we can interpolate a polynomial to evaluate at k alphas
    # to get the original message
    correct_symbol_indices = [alpha for alpha in range(n) if E(alpha) != 0]
    correct_symbols = [codeword[index] for index in correct_symbol_indices]

    interpolated_symbols = ring.lagrange_polynomial(zip(correct_symbol_indices, correct_symbols))

    original_message_coefficients = [interpolated_symbols(index) for index in range(k)]

    return PolynomialRing(ring, 'x')(original_message_coefficients)


def get_factors_with_less_errors(factors, xs, ys, num_of_errors, k):
    """
    Method to obtain factors which have at most num_of_errors errors and degree <=k
    ------------------------------------------------------
    Parameters:
    :param factors       - list of polynomials f for which to check if f(x_i) != y_i for at most num_of_error values
    :param xs            - list of x values
    :param ys            - list of y values
    :param num_of_errors - number of errors in the given codeword
    :param k             - maximum degree of factor
    :return a list of all polynomials f ∈ factors such that their degree is at most k and have at most num_of_errors
            errors
    This is done in a brute force manner, checking each factor against every x_i, y_i pairing
    """
    good_factors = []
    for factor in factors:
        if factor.degree() > k:
            continue
        current_errors = 0
        for x, y in zip(xs, ys):
            if factor(x) != y:
                current_errors += 1
                if current_errors > num_of_errors:
                    break
        if current_errors <= num_of_errors:
            good_factors.append(factor)
    return good_factors


def get_p_from_factor(factor, ring):
    """
    Method to obtain the Polynomial P from factor Y-P(X)
    ---
    Parameters:
    :param factor: bi-variate polynomial which is a factor of Q
    :param ring: ring over which Q is
    :return: uni-variate representation of P(X)
    """
    x, y = ring.gens()
    if (factor - y).is_univariate():
        return (y - factor).univariate_polynomial()
    return None


def rs_list_decoder(codeword, k, num_of_errors, GF):
    n = len(codeword)
    D = int(sqrt(2 * k * n))

    equations = [[] for _ in range(n)]

    for alpha in range(n):
        for j in range(D // k + 1):
            for i in range(D - k * j + 1):
                y_coeff = codeword[alpha]
                if y_coeff == 0 and j == 0:  # Avoiding exception for 0^0
                    y_coeff = 1
                equations[alpha].append(GF(alpha ** i * y_coeff ** j))

    equations_matrix = Matrix(GF, equations)
    unknowns = equations_matrix.right_kernel().matrix()[0]

    qij = [[] for _ in range(D // k + 1)]
    index = 0
    for j in range(D // k + 1):
        for i in range(D - k * j + 1):
            qij[j].append(unknowns[index])
            index += 1

    ring = PolynomialRing(GF, ['x', 'y'])
    Q = ring(0)
    x, y = ring.gens()

    for j in range(len(qij)):
        for i in range(len(qij[j])):
            Q += qij[j][i] * x ** i * y ** j

    factors = Q.factor()
    factors_list = []
    for f in list(factors):
        p = get_p_from_factor(f[0], ring)
        if p is not None:
            factors_list.append(p)

    if len(factors_list) == 0:
        return None

    # Obtain the factors with less than num_of_errors errors
    good_factors = get_factors_with_less_errors(factors_list, list(range(n)), codeword, num_of_errors, k)

    # Evaluate the obtained factors at the first k alphas of the field to obtain a list of polynomial coefficients
    # which should contain the original message
    alphas = list(range(k))
    msg_list = []
    for f in good_factors:
        current_msg = []
        for a in alphas:
            current_msg.append(f(a))
        msg_list.append(current_msg)

    return msg_list


"""
    TESTS:
    How to run the test suite:
    1) Create a list (or lists) containing: a message (list of coefficients), a galois field and number of errors
    2) Concatenate them into a list L
    3) Call test_suite(L)
    The return value is a dictionary with the information of the total amount of tests ran and division of successes
    and failures of each decoder
"""

# Global variables
num_of_polys_per_k = 5
num_of_params = 10

# Finite fields:
GF7 = FiniteField(7)
GF97 = FiniteField(97)
GF929 = FiniteField(929)

ks_for_gf7 = [3]
ks_for_gf97 = [3, 15, 30, 45]
ks_for_gf929 = [3, 45, 100, 200, 400]


def test(msg, n, gf=FiniteField(7), errors=0, should_print=False):
    ring = PolynomialRing(gf, 'x')
    result = (None, None)
    if should_print:
        print("Original Message: ", msg)

    encoded_msg = rs_encoder(msg, n, gf)
    if should_print:
        print("Encoded Message: ", encoded_msg.list())

    received_codeword = error_generator(encoded_msg, errors, ring)[0]
    if should_print:
        print("Encoded Message with 2 errors: ", received_codeword.list())

    unique_decoded = rs_decoder(received_codeword.list(), len(msg), num_of_errors=errors, gf=gf)
    try:
        assert unique_decoded.list() == msg
        result = (True, None)
        if should_print:
            print("Unique Decoded Successfully: ", unique_decoded.list())
    except:
        result = (False, None)
        if should_print:
            print("Failed Unique Decoding: ", unique_decoded.list())

    list_decoded = None
    try:
        list_decoded = rs_list_decoder(received_codeword.list(), k=len(msg), num_of_errors=errors, GF=gf)
        assert msg in list_decoded
        result = (result[0], True)
        if should_print:
            print("List Decoded Successfully: ", list_decoded)
    except:
        result = (result[0], False)
        if should_print:
            print("Failed List Decoding: ", list_decoded)

    return result


def test_suite(runs):
    results = {}

    for run in runs:
        msg = run[0]
        n = run[1]
        gf = run[2]
        errors = run[3]

        # print(f"Running test({msg}, {n}, {gf}, {errors})")
        key = n
        run_result = {}
        if key in results:
            run_result = results[key]
        else:
            run_result["runs"] = 0
            run_result["ud"] = 0
            run_result["ld"] = 0

        result = test(msg, n, gf, errors)
        run_result["runs"] += 1
        # Check if unique decoder was successful
        if result[0]:
            run_result["ud"] += 1

        # Check if list decoder was successful
        if result[1]:
            run_result["ld"] += 1

        results[key] = run_result

    return results


def randomize_poly(gf, k):
    coeffs = []
    q = gf.characteristic()
    for _ in range(k):
        coeffs.append(random.randint(0, q - 1))
    return coeffs


def test_11(gf, ks):
    """
    Test 1.1: Percentage of successful decoding with no errors and increasing length of encoding n
    :param gf: galois field
    :param ks: k values list
    :return: dictionary of results
    """
    q = gf.characteristic()
    errors = 0

    polynomials = {}
    # Generate num_of_polys_per_k polynomials per k
    for k in ks:
        k_polys = [randomize_poly(gf, k) for _ in range(num_of_polys_per_k)]
        polynomials[k] = k_polys

    results_for_k = {}

    for k in polynomials:
        runs = []
        p_list = polynomials[k]

        # Generate num_of_polys_per_k different encoding lengths
        ns = [random.randint(k + 1, q) for _ in range(num_of_params)]
        ns.sort()

        # Generate runs
        for poly in p_list:
            p_runs = [[poly, ns[index], gf, errors] for index in range(len(ns))]
            runs.extend(p_runs)

        results_for_k[k] = test_suite(runs)

    return results_for_k


def test_12(gf, ks):
    """
    Test 1.2: Percentage of successful decoding with 2 errors and increasing length of encoding n
    :param gf: galois field
    :param ks: k values list
    :return: dictionary of results
    """
    q = gf.characteristic()
    errors = 2

    polynomials = {}
    # Generate num_of_polys_per_k polynomials per k
    for k in ks:
        k_polys = [randomize_poly(gf, k) for _ in range(num_of_polys_per_k)]
        polynomials[k] = k_polys

    results_for_k = {}

    for k in polynomials:
        runs = []
        p_list = polynomials[k]

        # Generate num_of_polys_per_k different encoding lengths
        ns = [random.randint(k + 1, q) for _ in range(num_of_params)]
        ns.sort()

        # Generate runs
        for poly in p_list:
            p_runs = [[poly, ns[index], gf, errors] for index in range(len(ns))]
            runs.extend(p_runs)

        results_for_k[k] = test_suite(runs)

    return results_for_k


def test_13(gf, ks):
    """
    Test 1.3: Percentage of successful decoding with increasing number of errors relative to the length of encoding n
    :param gf: galois field
    :param ks: k values list
    :return: dictionary of results
    """
    q = gf.characteristic()

    polynomials = {}
    # Generate num_of_polys_per_k polynomials per k
    for k in ks:
        k_polys = [randomize_poly(gf, k) for _ in range(num_of_polys_per_k)]
        polynomials[k] = k_polys

    results_for_k = {}

    for k in polynomials:
        runs = []
        p_list = polynomials[k]

        # Generate num_of_params (default 10) different encoding lengths per k
        ns = [random.randint(k + 1, q) for _ in range(num_of_params)]
        ns.sort()

        # Generate a number of errors equal to 70% of the maximum errors RS can decode from a length n codeword
        errors = []
        for n in ns:
            d = n - k + 1
            max_errors = (d - 1) // 2
            errors.append(int(max_errors * 0.7))

        # Generate the runs
        for poly in p_list:
            p_runs = [[poly, ns[index], gf, errors[index]] for index in range(len(errors))]
            runs.extend(p_runs)

        results_for_k[k] = test_suite(runs)

    return results_for_k


def test_14(gf, ks):
    """
    Test 1.4: Percentage of successful decoding with a constant encoding length n and increasing number of errors e
    :param gf: galois field
    :param ks: k values list
    :return: dictionary of results
    """
    q = gf.characteristic()
    n = q

    polynomials = {}
    errors_for_k = {}
    # Generate num_of_polys_per_k polynomials per k and calculate maximum error size
    for k in ks:
        k_polys = [randomize_poly(gf, k) for _ in range(num_of_polys_per_k)]
        polynomials[k] = k_polys
        max_error_for_nk = (n - k) // 2
        # Generate num_of_params errors from 0 to floor((n-k)/2)
        errors = [random.randint(0, max_error_for_nk) for _ in range(num_of_params)]
        errors.sort()
        errors_for_k[k] = errors

    results_for_k = {}

    for k in polynomials:
        runs = []
        p_list = polynomials[k]
        for poly in p_list:
            error_list = errors_for_k[k]
            p_runs = [[poly, n, gf, error_list[index]] for index in range(len(error_list))]
            runs.extend(p_runs)

        results_for_k[k] = test_suite(runs)

    return results_for_k


def test_211(gf, ks):
    """
    Test 2.1.1: Percentage of successful decoding with encoding length n equal to the original message length k,
    without errors
    :param gf: galois field
    :param ks: k values list
    :return: dictionary of results
    """
    errors = 0

    polynomials = {}
    # Generate num_of_polys_per_k polynomials per k
    for k in ks:
        k_polys = [randomize_poly(gf, k) for _ in range(num_of_polys_per_k)]
        polynomials[k] = k_polys

    results_for_k = {}

    # Generate runs
    for k in polynomials:
        p_list = polynomials[k]
        runs = [[poly, k, gf, errors] for poly in p_list]
        results_for_k[k] = test_suite(runs)

    return results_for_k


def test_212(gf, ks):
    """
    Test 2.1.2: Percentage of successful decoding with encoding length n equal to the original message length k,
    with 1 error
    :param gf: galois field
    :param ks: k values list
    :return: dictionary of results
    """
    errors = 1

    polynomials = {}
    # Generate num_of_polys_per_k polynomials per k
    for k in ks:
        k_polys = [randomize_poly(gf, k) for _ in range(num_of_polys_per_k)]
        polynomials[k] = k_polys

    results_for_k = {}

    # Generate runs
    for k in polynomials:
        p_list = polynomials[k]
        runs = [[poly, k, gf, errors] for poly in p_list]
        results_for_k[k] = test_suite(runs)

    return results_for_k


def test_213(gf, ks):
    """
    Test 2.1.3: Percentage of successful decoding with encoding length n equal to the original message length k,
    with 2 errors
    :param gf: galois field
    :param ks: k values list
    :return: dictionary of results
    """
    errors = 2

    polynomials = {}
    # Generate num_of_polys_per_k polynomials per k
    for k in ks:
        k_polys = [randomize_poly(gf, k) for _ in range(num_of_polys_per_k)]
        polynomials[k] = k_polys

    results_for_k = {}

    # Generate runs
    for k in polynomials:
        p_list = polynomials[k]
        runs = [[poly, k, gf, errors] for poly in p_list]
        results_for_k[k] = test_suite(runs)

    return results_for_k


def test_22(gf, ks):
    """
    Test 2.2: Percentage of successful decoding with number of errors e > floor((d-1) / 2)
    :param gf: galois field
    :param ks: k values list
    :return: dictionary of results
    """
    q = gf.characteristic()
    n = q

    polynomials = {}
    errors_for_k = {}
    # Generate num_of_polys_per_k polynomials per k
    for k in ks:
        k_polys = [randomize_poly(gf, k) for _ in range(num_of_polys_per_k)]
        polynomials[k] = k_polys
        max_error_for_k = (n - k) // 2
        # Make sure there are (n+max_errors)//2 > max_errors that the code should be able
        # to handle for encoding length n
        errors_for_k[k] = (n + max_error_for_k) // 2

    results_for_k = {}

    # Generate runs
    for k in polynomials:
        p_list = polynomials[k]
        runs = [[poly, n, gf, errors_for_k[k]] for poly in p_list]
        results_for_k[k] = test_suite(runs)

    return results_for_k


"""
    METHODS FOR PLOTTING RESULTS
"""


def plot_success_rate(results, decoder):
    success_rate = {}
    n_values = {}
    for k in results:
        success_rate[k] = []
        n_values[k] = []
        for n in results[k]:
            success_rate[k].append(results[k][n][decoder] / results[k][n]['runs'])
            n_values[k].append(n)

    for k in success_rate:
        plt.plot(n_values[k], success_rate[k], label=f"k={k}", marker="o", markersize=3)

    plt.xlabel('n')
    decoder_str = "Unique Decoder" if decoder == 'ud' else "List Decoder"
    plt.ylabel(f"Success rate for {decoder_str}")
    plt.legend()
    plt.show()


def plot_success_rate_point(results, decoder):
    success_rate = {}
    n_values = {}
    for k in results:
        success_rate[k] = []
        n_values[k] = []
        for n in results[k]:
            success_rate[k].append(results[k][n][decoder] / results[k][n]['runs'])
            n_values[k].append(n)

    for k in success_rate:
        plt.plot(n_values[k], success_rate[k], label=f"k={k}", marker="o", markersize=3)
        for i in range(len(n_values[k])):
            plt.annotate(f"({n_values[k][i]}, {float(success_rate[k][i]):.2f})", (n_values[k][i] + 0.01, success_rate[k][i]))
    plt.xlabel('n')
    decoder_str = "Unique Decoder" if decoder == 'ud' else "List Decoder"
    plt.ylabel(f"Success rate for {decoder_str}")
    plt.legend()
    plt.show()


def plot_success_rate_difference(results):
    ud_success_rate = {}
    ld_success_rate = {}
    n_values = {}
    for k in results:
        ud_success_rate[k] = []
        ld_success_rate[k] = []
        n_values[k] = []
        for n in results[k]:
            ud_success_rate[k].append(results[k][n]['ud'] / results[k][n]['runs'])
            ld_success_rate[k].append(results[k][n]['ld'] / results[k][n]['runs'])
            n_values[k].append(n)

    success_rate = {}
    for k in ud_success_rate:
        success_rate[k] = []
        for ud_rate, ld_rate in zip(ud_success_rate[k], ld_success_rate[k]):
            success_rate[k].append(ud_rate - ld_rate)

    for k in success_rate:
        plt.plot(n_values[k], success_rate[k], label=f"k={k}", marker="o", markersize=3)

    plt.xlabel('n')
    plt.ylabel(f"Success rate difference between unique and list decoders")
    plt.legend()
    plt.show()


def plot_success_rate_difference_point(results):
    ud_success_rate = {}
    ld_success_rate = {}
    n_values = {}
    for k in results:
        ud_success_rate[k] = []
        ld_success_rate[k] = []
        n_values[k] = []
        for n in results[k]:
            ud_success_rate[k].append(results[k][n]['ud'] / results[k][n]['runs'])
            ld_success_rate[k].append(results[k][n]['ld'] / results[k][n]['runs'])
            n_values[k].append(n)

    success_rate = {}
    for k in ud_success_rate:
        success_rate[k] = []
        for ud_rate, ld_rate in zip(ud_success_rate[k], ld_success_rate[k]):
            success_rate[k].append(ud_rate - ld_rate)

    for k in success_rate:
        plt.plot(n_values[k], success_rate[k], label=f"k={k}", marker="o", markersize=3)
        for i in range(len(n_values[k])):
            plt.annotate(f"({n_values[k][i]}, {float(success_rate[k][i]):.2f})", (n_values[k][i] + 0.01, success_rate[k][i]))

    plt.xlabel('n')
    plt.ylabel(f"Success rate difference between unique and list decoders")
    plt.legend()
    plt.show()


def plot_test_success_rate(results, string):
    print(f"Success rate of Unique Decoder {string}:")
    plot_success_rate(results, 'ud')

    print(f"Success rate of List Decoder {string}:")
    plot_success_rate(results, 'ld')

    print(f"Success rate difference between unique and list decoders {string}:")
    plot_success_rate_difference(results)

    plt.show()


def plot_test_success_rate_point(results, string):
    print(f"Success rate of Unique Decoder {string}:")
    plot_success_rate_point(results, 'ud')

    print(f"Success rate of List Decoder {string}:")
    plot_success_rate_point(results, 'ld')

    print(f"Success rate difference between unique and list decoders {string}:")
    plot_success_rate_difference_point(results)

    plt.show()


# def plot_test_success_with_errors(results):
#     print("Success rate of Unique Decoder with increasing number of errors:")
#     plot_success_rate(results, 'ud')
#
#     print("Success rate of List Decoder with increasing number of errors:")
#     plot_success_rate(results, 'ld')
#
#     print("Success rate of difference between unique and list decoders with increasing number of errors:")
#     plot_success_rate_difference(results)
#
#     plt.show()


def plot_test_success_with_errors_point(results): # Used for test 1.4
    print("Success rate of Unique Decoder with increasing number of errors:")
    plot_success_rate_point(results, 'ud')

    print("Success rate of List Decoder with increasing number of errors:")
    plot_success_rate_point(results, 'ld')

    print("Success rate of difference between unique and list decoders with increasing number of errors:")
    plot_success_rate_difference_point(results)

    plt.show()


def plot_compare_21(t0_res, t1_res, t2_res, decoder):
    success_rate_per_error = {}
    for k in t1_res:
        s_rate_no_errors = t0_res[k][k][decoder] / t0_res[k][k]['runs']
        s_rate_one_error = t1_res[k][k][decoder] / t1_res[k][k]['runs']
        s_rate_two_errors = t2_res[k][k][decoder] / t2_res[k][k]['runs']
        success_rate_per_error[k] = [s_rate_no_errors, s_rate_one_error, s_rate_two_errors]

    errors = [0, 1, 2]
    decoder_str = "Unique Decoder" if decoder == 'ud' else "List Decoder"
    for k in success_rate_per_error:
        plt.plot(errors, success_rate_per_error[k], label=f"k={k}", marker="o", markersize=3)
    plt.xlabel('Errors')
    plt.ylabel(f'Success rate for the {decoder_str}')
    plt.legend()
    plt.show()


def test_decoders(gf, ks):
    print("Test 1.1:")
    t11_res = test_11(gf, ks)
    plot_test_success_rate(t11_res, "without errors")

    print("Test 1.2:")
    t12_res = test_12(gf, ks)
    plot_test_success_rate(t12_res, "with 2 errors")

    print("Test 1.3:")
    t13_res = test_13(gf, ks)
    plot_test_success_rate(t13_res, "with errors equal to 70% maximum error relative to n")

    print("Test 1.4:")
    t14_res = test_14(gf, ks)
    plot_test_success_with_errors_point(t14_res)

    print("Test 2.1.1:")
    t211_res = test_211(gf, ks)
    plot_test_success_rate_point(t211_res, "with n=k and without errors")

    print("Test 2.1.2:")
    t212_res = test_212(gf, ks)
    plot_test_success_rate_point(t212_res, "with n=k and with 1 error")

    print("Test 2.1.3:")
    t213_res = test_213(gf, ks)
    plot_test_success_rate_point(t213_res, "with n=k and with 2 errors")

    print("Success rate for k=n with and without errors for the Unique Decoder:")
    plot_compare_21(t211_res, t212_res, t213_res, 'ud')

    print("Success rate for k=n with and without errors for the List Decoder:")
    plot_compare_21(t211_res, t212_res, t213_res, 'ld')

    print("Test 2.2:")
    t22_res = test_22(gf, ks)
    plot_test_success_with_errors_point(t22_res)


"""
TESTS ARE HERE
"""
# test_decoders(GF97, ks_for_gf7)
