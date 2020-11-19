import numpy as np
from helper import helper
from itertools import combinations

def get_interatomics(xyz):
    # Build OptKing internal coordinates of interatomic distances
    natoms = xyz.shape[0]
    # Indices of unique interatomic distances, lower triangle row-wise order
    indices = np.asarray(np.tril_indices(natoms,-1)).transpose(1,0)
    interatomics = []
    for i in indices:
        idx1, idx2 = i
        interatomics.append(helper.STRE(idx1, idx2))
    return interatomics


def interatomic_forces(xyz, xyzgrad):
    """
    Parameters
    ----------
    xyz : A NumPy array of Cartesian coordinates
    xyzgrad : A NumPy array of gradient of Cartesian coordinates
    UNITS MUST AGREE 

    Returns
    -------
    dforces : A NumPy array of forces on interatomic distances 
    """
    interatomics = get_interatomics(xyz)
    # this works: have to use same internal coordinate parameter definitions as CFOUR/Psi4. 
    # In this way, gradients in internals are somewhat arbitrary; they change based on internal coordinate definitions.
    # Because of this, interatomic distance gradients are theoretically sound, since it is arbitrary anyway
    # IF Cartesians=Bohr and Gradients=Hartree/Bohr, angular gradients are in Hartree/Radian
    #interatomics = [helper.STRE(0,1), helper.STRE(0,2), helper.BEND(2,0,1)]
    #interatomics = [helper.STRE(0,1), helper.STRE(1,2), helper.BEND(2,1,0)]

    forces = helper.qForces(interatomics, xyz, xyzgrad.flatten())
    # TODO at some point, will have to worry about order
    return forces
 
    
#import psi4
#psi4.core.be_quiet()
#h2o = psi4.geometry(
#'''
#H            0.000000000000     0.000000000000     0.950000000000 
#H            0.000000000000     0.872305301500    -0.376275777700 
#O            0.000000000000     0.000000000000     0.000000000000 
#''')
#
#psi4.set_options({'scf_type': 'pk'})
#g, wfn = psi4.gradient('scf/6-31g', return_wfn = True)
#
## geometry in Bohr, grad in Hartrees/Bohr, Hessian in Hartrees/Bohr/Bohr
#geom = np.array(h2o.geometry())
#grad = np.array(g)
#h, wfn = psi4.hessian('scf/6-31g', return_wfn = True)
#hess = np.array(h)
#
## convert hessian to angstrom
#hess /= 0.529177249**2
#interatomics = get_interatomics(geom)
#inthess = helper.convertHessianToInternals(hess, interatomics, geom, grad.flatten())
#
#dforces = interatomic_forces(geom, grad)
#print("Hartrees/Angs", dforces/0.529177249)
#
#
#
#
#print(inthess)


#print("AttoJoul/Bohr", dforces*4.35974)
#print("AttoJoul/Angs", dforces*4.35974/0.529177)
#print("psi4 r1 hartree/bohr", -0.050576 * 0.529177 / 4.35974)
#print("psi4 a1 hartree/degree",  0.001637 / 4.35974 * (180/np.pi))


