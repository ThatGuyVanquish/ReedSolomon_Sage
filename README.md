# Reed Solomon Encoding and Decoding algorithm implementation with Sage using Python

### This repository is my implementation of a Reed Solomon encoder, unique decoder (Berlekamp-Welch algorithm) and list decoder (Sudan algorithm) using Sage with Python, as a part of a university course Topics in Error Correcting Codes.

### Execution instructions:
Option 1: The method “test_decoders(GF, k_list)” accepts a FiniteField(q) object (GF) and
a list of integers (k_list) which consists of integers in the range of [1, 𝑞], runs all of the
tests, randomizing polynomials and errors based on the given arguments and plots the
statistics over all of the tests ran.
Note that to change the parameters of how many polynomials and how many different
values (be it the encoded length 𝑛 or the number of errors 𝑒 in the different tests) to use,
look for the parameters “num_of_num_of_polys_per_k” and “num_of_params” and
change them as needed.
Option 2: To run methods individually:
1. rs_encoder ≔ encoder
2. rs_decoder ≔ unique decoder (Berlekamp-Welch)
3. rs_list_decoder ≔ list decoder (Sudan)
4. error_generator ≔ method to generate errors in the given polynomial
5. randomize_poly:= method to generate a random polynomial of length k over a
finite field gf.
