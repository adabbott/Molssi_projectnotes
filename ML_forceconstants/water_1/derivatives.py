import psi4
from peslearn.ml import NeuralNetwork
from peslearn import InputProcessor
import numpy as np
import scipy 
import torch
import sympy
from compute_energy import pes
import Btensors
np.set_printoptions(threshold=5000, linewidth=200, precision=5, suppress=True)
torch.set_printoptions(threshold=5000, linewidth=200, precision=5)
bohr2ang = 0.529177249
hartree2J = 4.3597443e-18
hartree2cm = 219474.63
amu2kg = 1.6605389e-27
ang2m = 1e-10
h = 6.6260701510e-34   # Plancks in J s
hbar = 1.054571817e-34 # Reduced Plancks constant J s
hbarcm = (hbar / hartree2J) * hartree2cm
c = 29979245800.0 # speed of light in cm/s
cmeter = 299792458 # speed of light in cm/s
hz2cm = 3.33565e-11

convert = np.sqrt(hartree2J/(amu2kg*ang2m*ang2m))/(c*2*np.pi)
convert2 = np.sqrt(hartree2J/(amu2kg*ang2m*ang2m*ang2m))/(c * 2 * np.pi)

convert_1 = (hartree2J / (ang2m**3 * amu2kg**(3/2) )) * np.sqrt(h) # (converts to 1 / s^2.5)

convert3 = np.cbrt(hartree2J/(amu2kg*ang2m*ang2m))/(c*2*np.pi)

convert4 = np.sqrt(hartree2J/(amu2kg*ang2m*ang2m*ang2m))/(c*2*np.pi)
convert5 = np.sqrt(hartree2J/(amu2kg*ang2m*ang2m*ang2m))/(c**2 *2*np.pi)

#                  |      1 / s^2 m                   |
convert6 = np.cbrt((hartree2J/(amu2kg*ang2m*ang2m*ang2m)) * cmeter ) / (c*2*np.pi)
convert7 = np.cbrt((hartree2J/(amu2kg*ang2m*ang2m*ang2m)) ) / (c*2*np.pi)

# Load NN model
nn = NeuralNetwork('model_data/PES.dat', InputProcessor(''), molecule_type='A2B')
params = {'layers': (64, 64), 'morse_transform': {'morse': True, 'morse_alpha': 1.2000000000000002}, 'pip': {'degree_reduction': False, 'pip': True}, 'scale_X': {'activation': 'tanh', 'scale_X': 'mm11'}, 'scale_y': 'std', 'lr': 0.8}
X, y, Xscaler, yscaler =  nn.preprocess(params, nn.raw_X, nn.raw_y)
model = torch.load('model_data/model.pt')

def transform(interatomics):
    """ Takes Torch Tensor (requires_grad=True) of interatomic distances, manually transforms geometry to track gradients, computes energy
        Hard-coded based on hyperparameters above. Returns: energy in units the NN model was trained on"""
    inp2 = -interatomics / 1.2
    inp3 = torch.exp(inp2)
    inp4 = torch.stack((inp3[0], inp3[1] + inp3[2], torch.sum(torch.pow(inp3[1:],2))), dim=0) # Careful! Degree reduce?
    inp5 = (inp4 * torch.tensor(Xscaler.scale_, dtype=torch.float64)) + torch.tensor(Xscaler.min_, dtype=torch.float64)
    out1 = model(inp5)
    energy = (out1 * torch.tensor(yscaler.scale_, dtype=torch.float64)) + torch.tensor(yscaler.mean_, dtype=torch.float64)
    return energy

def cart2distances(cart):
    """Transforms cartesian coordinate torch Tensor (requires_grad=True) into interatomic distances"""
    natom = cart.size()[0]
    ndistances = int((natom**2 - natom) / 2)
    distances = torch.zeros((ndistances), requires_grad=True, dtype=torch.float64)
    count = 0
    for i,atom1 in enumerate(cart):
        for j,atom2 in enumerate(cart):
            if j > i:
                distances[count] = torch.norm(cart[i]- cart[j])
                count += 1
    return distances

def cart2internals(cart, internals):
    values = Btensors.ad_intcos.qValues(internals, cart)   # Generate internal coordinates from cartesians
    return values
      
def differentiate_nn(energy, geometry, order=1):
    # The grad_tensor starts of as a single element, the energy. Then it becomes the gradient, hessian, cubic ... 
    # depending on value of 'order'
    grad_tensor = energy
    # The number of geometry parameters. Returned gradient tensor will have this size in all dimensions
    nparams = torch.numel(geometry)
    # The shape of first derivative. Will be adjusted at higher order
    shape = [nparams]
    count = 0
    while count < order:
        gradients = []
        for value in grad_tensor.flatten():
            g = torch.autograd.grad(value, geometry, create_graph=True)[0].reshape(nparams)
            gradients.append(g)
        grad_tensor = torch.stack(gradients).reshape(tuple(shape))
        shape.append(nparams)
        count += 1
    return grad_tensor

def get_interatomics(natoms):
    # Build autodiff-OptKing internal coordinates of interatomic distances
    #natoms = xyz.shape[0]
    # Indices of unique interatomic distances, lower triangle row-wise order
    indices = np.asarray(np.tril_indices(natoms,-1)).transpose(1,0)
    interatomics = []
    for i in indices:
        idx1, idx2 = i
        interatomics.append(Btensors.ad_intcos.STRE(idx1, idx2))
    return interatomics

def cartesian_freq(hess, m):
    """Get harmonic frequencies in wavenumbers from Cartesian Hessian in Hartree/ang^2. 
    m is a numpy array containing mass in amu for each atom, same order as Hessian. size:natom"""
    m = np.repeat(m,3)
    M = 1 / np.sqrt(m)
    M = np.diag(M)
    Hmw = M.dot(hess).dot(M)
    cartlamda, cartL = np.linalg.eig(Hmw)
    idx = cartlamda.argsort()[::-1]
    cartlamda = cartlamda[idx]
    freqs = np.sqrt(cartlamda) * convert
    return freqs[:-6], cartL

def internal_freq(hess, B1, m):
    """
    Get harmonic frequencies with GF method. 
    hess : numpy array of hessian in internal coordinates Hartree/ang^2
    B1 : 1st order B tensor in terms of internal coordinates in Hessian 
    m : numpy array of masses in amu
    Returns 
    -------
    Frequencies in wavenumbers, normal coordinates
    """
    m = np.repeat(m,3)
    M = 1 / m
    G = np.einsum('in,jn,n->ij', B1, B1, M)
    GF = G.dot(hess)
    intlamda, intL = np.linalg.eig(GF)
    idx = intlamda.argsort()[::-1]
    intlamda = intlamda[idx]
    freqs = np.sqrt(intlamda) * convert
    return freqs, intL

def tmp_internal_freq(hess, B1, m):
    """
    Get harmonic frequencies with GF method. 
    hess : numpy array of hessian in internal coordinates Hartree/ang^2
    B1 : 1st order B tensor in terms of internal coordinates in Hessian 
    m : numpy array of masses in amu
    Returns 
    -------
    Frequencies in wavenumbers, normal coordinates
    """
    m = np.repeat(m,3)
    M = 1 / m
    G = np.einsum('in,jn,n->ij', B1, B1, M)
    Gt = scipy.linalg.fractional_matrix_power(G, 0.5)
    Fp = Gt.dot(hess).dot(Gt)
    intlamda, intL = np.linalg.eig(Fp)
    L = Gt.dot(intL)
    # Return Frequencies and 'L matrix' (mass weighted) in increasing order
    idx = intlamda.argsort()
    intlamda = intlamda[idx]
    freqs = np.sqrt(intlamda) * convert
    return freqs, L[:,idx]

def cartcubic2intcubic(cart_cubic, int_hess, B1, B2):
    G = np.dot(B1, B1.T)
    Ginv = np.linalg.inv(G)
    A = np.dot(Ginv, B1)
    # First: just do what it says
    tmp1 = np.einsum('ia,jb,kc,abc->ijk', A, A, A, cart_cubic)
    tmp2 = np.einsum('lmn,il,jm,kn->ijk', B2, int_hess, A, A)
    tmp3 = np.einsum('lmn,jl,im,kn->ijk', B2, int_hess, A, A)
    tmp4 = np.einsum('lmn,kl,im,jn->ijk', B2, int_hess, A, A)
    int_cubic = tmp1 - tmp2 - tmp3 - tmp4
    return int_cubic

def cartderiv2intderiv(derivative_tensor, B1):
    """
    Converts cartesian derivative tensor (gradient, Hessian, cubic, quartic ...) into internal coordinates
    Only valid at stationary points for Hessians and above.

    Parameters
    ----------   
    derivative_tensor : np.ndarray
        Tensor of nth derivative in Cartesian coordinates 
    B1 : np.ndarray
        B-matrix converting Cartesian coordinates to internal coordinates
    """
    G = np.dot(B1, B1.T)
    Ginv = np.linalg.inv(G)
    A = np.dot(Ginv, B1)
    dim = len(derivative_tensor.shape)
    if dim == 1:
        int_tensor = np.einsum('ia,a->i', A, derivative_tensor)
    elif dim == 2:
        int_tensor = np.einsum('ia,jb,ab->ij', A, A, derivative_tensor)
    elif dim == 3:
        int_tensor = np.einsum('ia,jb,kc,abc->ijk', A, A, A, derivative_tensor)
    elif dim == 4:
        int_tensor = np.einsum('ia,jb,kc,ld,abcd->ijkl', A, A, A, A, derivative_tensor)
    else:
        raise Exception("Too many dimensions. Add code to function")
    return int_tensor

def intcubic2cartcubic(intcubic, inthess, B1, B2):
    tmp1 = np.einsum('ia,jb,kc,ijk->abc', B1, B1, B1, intcubic)
    tmp2 = np.einsum('iab,jc,ij->abc', B2, B1, inthess)
    tmp3 = np.einsum('ica,jb,ij->abc', B2, B1, inthess)
    tmp4 = np.einsum('ibc,ja,ij->abc', B2, B1, inthess)
    cart_cubic = tmp1 + tmp2 + tmp3 + tmp4
    return cart_cubic
    
def intderiv2cartderiv(derivative_tensor, B1):
    """ 
    Converts cartesian derivative tensor (gradient, Hessian, cubic, quartic ...) into internal coordinates
    Only valid at stationary points for Hessians and above.

    Parameters
    ----------   
    derivative_tensor : np.ndarray
        Tensor of nth derivative in internal coordinates 
    B1 : np.ndarray
        B-matrix converting internal coordinates to Cartesian coordinates
    """
    dim = len(derivative_tensor.shape)
    if dim == 1:
        cart_tensor = np.einsum('ia,i->a', B1, derivative_tensor)
    elif dim == 2:
        cart_tensor = np.einsum('ia,jb,ij->ab', B1, B1, derivative_tensor)
    elif dim == 3:
        cart_tensor = np.einsum('ia,jb,kc,ijk->abc', B1, B1, B1, derivative_tensor)
    elif dim == 4:
        cart_tensor = np.einsum('ia,jb,kc,ld,ijkl->abcd', B1, B1, B1, B1, derivative_tensor)
    else:
        raise Exception("Too many dimensions. Add code to function to compute")
    return cart_tensor

cartesians = torch.tensor([[ 0.0000000000,0.0000000000,0.9496765298],
                           [ 0.0000000000,0.8834024755,-0.3485478124],
                           [ 0.0000000000,0.0000000000,0.0000000000]], dtype=torch.float64, requires_grad=True)
cartesians_nograd = torch.tensor([[ 0.0000000000,0.0000000000,0.9496765298],
                           [ 0.0000000000,0.8834024755,-0.3485478124],
                           [ 0.0000000000,0.0000000000,0.0000000000]], dtype=torch.float64, requires_grad=False)
#
# HH H1O H2O
eq_geom = [1.570282260121,0.949676529800,0.949676529800]
distances = torch.tensor(eq_geom, dtype=torch.float64, requires_grad=True)
print("Equilibrium geometry and energy: ", eq_geom, pes(eq_geom,cartesian=False)) # Test computation

# Compute internal coordinate Hessian wrt starting from both interatomic distances and cartesian coordinates, this works
#computed_distances = cart2distances(cartesians)
#E = transform(computed_distances)
#hint =  differentiate_nn(E, computed_distances, order=2)
#hcart =  differentiate_nn(E, cartesians, order=2)

# Psi4 hessian and frequencies
psi4.core.be_quiet()
h2o = psi4.geometry(
'''
H 0.0000000000 0.0000000000 0.9496765298
H 0.0000000000 0.8834024755 -0.3485478124
O 0.0000000000 0.0000000000 0.0000000000
no_com
no_reorient
''')
psi4.set_options({'scf_type': 'pk'})
freq, wfn = psi4.frequencies('scf/6-31g', return_wfn = True)
print("Psi4 analytic frequencies")
print(np.sort(np.array(wfn.frequencies()))[::-1])
psihess = np.array(wfn.hessian())
psihess /= 0.529177249**2

#m = np.array([1.007825032230, 1.007825032230, 15.994914619570])
#
#psi4freq, junk = cartesian_freq(psihess, m)
#print("Manually computed frequencies with Psi4 Hessian", psi4freq)
#
#nnfreq, junk = cartesian_freq(hcart.detach().numpy(), m)
#print("Manually computed frequencies with NN with Cartesian Hessian", nnfreq)
#
#nnfreq2, junk = internal_freq(hint.detach().numpy(), get_interatomics(3), cartesians, m)
#print("Manually computed frequencies with NN with interatomic distance coordinate Hessian", nnfreq2)
#
#internals = [Btensors.ad_intcos.STRE(0,2), Btensors.ad_intcos.STRE(1,2), Btensors.ad_intcos.BEND(0,2,1)]
#curvi_inthess = cartHess2intHess(hcart.detach().numpy(), internals, cartesians)
#nnfreq3, L = internal_freq(curvi_inthess, internals, cartesians, m)
#print("Manually computed frequencies with NN with curvilinear internal coordinate Hessian", nnfreq3)



def quadratic(hess, m, L, B):
    """internal coordinate hessian, Mass of each atom, G 1/2 dotted with eigenvectors of hessian, and B tensor"""
    M = np.sqrt(1 / np.repeat(m,3))
    inv_trans_L = np.linalg.inv(L).T 
    little_l = np.einsum('a,ia,ir->ar', M, B, inv_trans_L)
    L1_tensor = np.einsum('ia,a,ar->ir', B, M, little_l)
    quadratic = np.einsum('ij,ir,js->rs', hess, L1_tensor, L1_tensor)
    print('quad',np.diagonal(np.sqrt(quadratic) * convert))
    return np.diagonal(np.sqrt(quadratic) * convert)
    
def cubic(hess, cubic, m, L, B1, B2):
    M = np.sqrt(1 / np.repeat(m,3))
    inv_trans_L = np.linalg.inv(L).T # Maybe dont tranpose? does inverse flip dimension? 
    little_l = np.einsum('a,ia,ir->ar', M, B1, inv_trans_L)
    L1 = np.einsum('ia,a,ar->ir', B1, M, little_l)
    L2 = np.einsum('iab,a,ar,b,bs->irs', B2, M, little_l, M, little_l)
    term1 = np.einsum('ijk,ir,js,kt->rst', cubic, L1, L1, L1)
    term2 = np.einsum('ij, irs, jt->rst', hess, L2, L1)
    term3 = np.einsum('ij, irt, js->rst', hess, L2, L1)
    term4 = np.einsum('ij,ist,jr->rst', hess, L2, L1)

    nc_cubic = term1 + term2 + term3 + term4                             # UNITS: Hartree / Ang^3 amu^3/2
    frac = (hbar / (2*np.pi*cmeter))**(3/2) 
    nc_cubic *= (1 / (ang2m**3 * amu2kg**(3/2)))                         # UNITS: Hartree / m^3 kg^3/2
    nc_cubic *= frac                                                     # UNITS: Hartree / m^(3/2) 
    nc_cubic *= (1 / 100**(3/2))                                         # UNITS: Hartree cm-1 ^ (3/2)
    # Multiply each element by appropriate 3 harmonic frequencies
    omega = np.array([1737.31536,3987.9131,4144.72382])**(-1/2)
    nc_cubic = np.einsum('ijk,i,j,k->ijk', nc_cubic, omega, omega, omega) # UNITS: Hartree
    # add minus sign and convert to cm-1
    nc_cubic *= -hartree2cm                                               # UNITS: cm-1
    print(nc_cubic)
    return nc_cubic



# Use Psi4 data first
#internals = [Btensors.ad_intcos.STRE(0,2), Btensors.ad_intcos.STRE(1,2), Btensors.ad_intcos.BEND(0,2,1)]
#psi4_inthess = cartHess2intHess(psihess, internals, cartesians)

#m = np.array([1.007825032230, 1.007825032230, 15.994914619570])
#f, L = internal_freq(psi4_inthess, internals, cartesians, m)
#print(f)

#B1 = Btensors.ad_btensor.autodiff_Btensor(internals, cartesians, order=1)
#B1 = B1.detach().numpy()
#quadratic(m, psi4_inthess, L, B1)
#cubic(psi4_inthess, L, B1, B2)



# Define curvilinear internal coordinates, 1st, 2nd order B tensors

# Genearte Cartesian Hessian with NN, convert to internal coordinates
#internal_coordinates =  cart2internals(cartesians, internals)
#print(internal_coordinates)
#hess_curvi = differentiate_nn(E, ad_internals, order=2)
#print(hess_curvi)
#hess_cart =  differentiate_nn(E, cartesians, order=2)
#hess_int = cartHess2intHess(hess_cart.detach().numpy(), internals, cartesians)
#m = np.array([1.007825032230, 1.007825032230, 15.994914619570])
#f, L = internal_freq(hess_int, internals, cartesians, m)
#print(f)
# Check: perform normal coordinate analysis, the L-tensor way
#quadratic(hess_int, m, L, B1)

#cubic_cart =  differentiate_nn(E, cartesians, order=3)
#quartic_cart =  differentiate_nn(E, computed_distances, order=4)

#hess_internals =  differentiate_nn(E, computed_distances, order=2)
#cubic_internals =  differentiate_nn(E, computed_distances, order=2)


# CHECK
#G = np.einsum('in,jn,n,n->ij', B, B, M, M)
#lamda = L.T.dot(G.dot(psi4_inthess)).dot(L)
#print(np.sqrt(lamda) * convert)



# Some accuracy as lost here, probably due to the gradient not being exactly zero.
#computed_distances = cart2distances(cartesians)
#E = transform(computed_distances)
#hess = differentiate_nn(E, cartesians, order=2)
#print('cart hess')
#print(hess)
#print(cartesian_freq(hess.detach().numpy(), m))
#print('converted cart hess to int hess')
#inthess = cartderiv2intderiv(hess.detach().numpy(), B1)
#print(inthess)
#print('backtransformed to cart hess')
#newcart = intderiv2cartderiv(inthess, B1)
#print(newcart)
#print(cartesian_freq(newcart, m))

internals = [Btensors.ad_intcos.STRE(0,2), Btensors.ad_intcos.STRE(1,2), Btensors.ad_intcos.BEND(0,2,1)]
interatomics = get_interatomics(3)
B1, B2 = Btensors.ad_btensor.fast_B(internals, cartesians_nograd)
B1, B2 = B1.detach().numpy(), B2.detach().numpy()
B1_idm, B2_idm = Btensors.ad_btensor.fast_B(interatomics, cartesians_nograd)
B1_idm, B2_idm = B1_idm.detach().numpy(), B2_idm.detach().numpy()
 
m = np.array([1.007825032230, 1.007825032230, 15.994914619570])
distances = torch.tensor([0.0, 0.0, 0.0], dtype=torch.float64, requires_grad=True)
computed_distances = cart2distances(cartesians)
temp = distances + computed_distances
E = transform(computed_distances)
interatomic_hess = differentiate_nn(E, computed_distances, order=2).detach().numpy()
cart_hess = intderiv2cartderiv(interatomic_hess, B1_idm)
curvilinear_hess = cartderiv2intderiv(cart_hess, B1)
psi4_curvihess = cartderiv2intderiv(psihess, B1)
print(curvilinear_hess)
print(psi4_curvihess)

interatomic_cubic = differentiate_nn(E, computed_distances, order=3).detach().numpy()
cart_cubic = intcubic2cartcubic(interatomic_cubic, interatomic_hess, B1_idm, B2_idm)
int_cubic = cartcubic2intcubic(cart_cubic, interatomic_hess, B1_idm, B2_idm)
# Check forward and reverse transformation
print(np.allclose(int_cubic,interatomic_cubic))
curvilinear_cubic = cartcubic2intcubic(cart_cubic, curvilinear_hess, B1, B2)

#f, L = internal_freq(curvilinear_hess, B1, m)
f, L_allen = tmp_internal_freq(curvilinear_hess, B1, m)
print(f)
print(L_allen)

b = quadratic(curvilinear_hess, m, L_allen, B1)
cubic(curvilinear_hess, curvilinear_cubic, m, L_allen, B1, B2)

# Try using as much Psi4 stuff as possible. Use Psi4 Cartesian hessian to get interatomic hessian, use that to get cartesian cubic, 
#interatomic_hess = cartderiv2intderiv(psihess, B1_idm) 
#cart_cubic = intcubic2cartcubic(interatomic_cubic, interatomic_hess, B1_idm, B2_idm)
#curvilinear_cubic = cartcubic2intcubic(cart_cubic, psi4_curvihess, B1, B2)
#f, L_allen = tmp_internal_freq(psi4_curvihess, B1, m)
#b = quadratic(psi4_curvihess, m, L_allen, B1)
#cubic(psi4_curvihess, curvilinear_cubic, m, L_allen, B1, B2)

# Identical frequencies, good!
#idm_f, idm_L = internal_freq(interatomic_hess, B1_idm, m)
#cart_f, cart_L = cartesian_freq(cart_hess, m)
#f, L = internal_freq(curvilinear_hess, B1, m)


