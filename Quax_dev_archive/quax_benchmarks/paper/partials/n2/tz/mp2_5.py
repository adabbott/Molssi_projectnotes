import psi4
import psijax

from data import molecule, basis_name

method = 'mp2'
d = psijax.core.partial_derivative(molecule, basis_name, method, order=5, address=(2,2,2,2,2))
print("MP2 ", basis_name, ' partial quintic')
print(d)
