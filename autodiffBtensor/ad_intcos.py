import torch
import math
import ad_v3d

# constants needed for TORS
fix_val_near_pi = 1.57
v3d_tors_angle_lim = 0.017
v3d_tors_cos_tol = 1e-10

def qValues(intcos, geom):
    """Calculates internal coordinates from cartesian geometry
    Parameters
    ---------
    intcos : list
        (nat) list of stretches, bends, etc...
    geom : ndarray
        (nat, 3) cartesian geometry
    Returns
    -------
    ndarray
        internal coordinate values
    """
    q = torch.stack([i.q(geom) for i in intcos])
    return q

class STRE(object):
    def __init__(self, a, b):
        if a < b: 
            atoms = (a,b) 
        else: 
            atoms = (b,a)
        self.A = atoms[0]
        self.B = atoms[1]

    def q(self, geom):
        return ad_v3d.dist(geom[self.A], geom[self.B])

    def new_q(self, coord1, coord2):
        return ad_v3d.dist(coord1, coord2)
        

class BEND(object):
    def __init__(self, a, b, c, bendType="REGULAR"):
        if a < c:
            atoms = (a, b, c)
        else:
            atoms = (c, b, a)
        self.A = atoms[0]
        self.B = atoms[1]
        self.C = atoms[2]
        self._bendType = bendType 
        self._axes_fixed = False

    def compute_axes(self, geom):
        u = ad_v3d.eAB(geom[self.B], geom[self.A])  # B->A
        v = ad_v3d.eAB(geom[self.B], geom[self.C])  # B->C

        if ad_v3d.are_parallel_or_antiparallel(u,v):
            self._bendType = "LINEAR"

        if self._bendType == "REGULAR":                   # not a linear-bend type
            self._w = ad_v3d.normalize(ad_v3d.cross(u,v)) # cross product and normalize
            self._x = ad_v3d.normalize(u + v)             # angle bisector
            return

        #tv1 = torch.tensor([1,0,0], dtype=torch.float64, requires_grad=True) 
        tv1 = torch.tensor([1,0,0], dtype=torch.float64) 
        #tmp_tv2 = torch.tensor([0,1,1], dtype=torch.float64, requires_grad=True)
        tmp_tv2 = torch.tensor([0,1,1], dtype=torch.float64)
        tv2 = ad_v3d.normalize(tmp_tv2)

        u_tv1 = ad_v3d.are_parallel_or_antiparallel(u, tv1)
        v_tv1 = ad_v3d.are_parallel_or_antiparallel(v, tv1)
        u_tv2 = ad_v3d.are_parallel_or_antiparallel(u, tv2)
        v_tv2 = ad_v3d.are_parallel_or_antiparallel(v, tv2)

        # handle both types of linear bends
        if not ad_v3d.are_parallel_or_antiparallel(u, v):
            self._w = ad_v3d.normalize(ad_v3d.cross(u, v))  # orthogonal vector
            self._x = ad_v3d.normalize(u + v)
        # u || v but not || to tv1.
        elif not u_tv1 and not v_tv1:
            self._w = ad_v3d.normalize(ad_v3d.cross(u, tv1))
            self._x = ad_v3d.normalize(ad_v3d.cross(self._w, u))
        # u || v but not || to tv2.
        elif not u_tv2 and not v_tv2:
            self._w = ad_v3d.normalize(ad_v3d.cross(u,tv2))
            self._x = ad_v3d.normalize(ad_v3d.cross(self._w, u))

        if self._bendType == "COMPLEMENT":
            w2 = torch.copy(self._w)
            self._w = -1.0 * self._x  # -w_normal -> x_complement
            self._x = w2
        return
        
    def q(self, geom):
        if not self._axes_fixed:
            self.compute_axes(geom)
        u = ad_v3d.eAB(geom[self.B], geom[self.A])  # B->A
        v = ad_v3d.eAB(geom[self.B], geom[self.C])  # B->C
        #origin = torch.zeros(3, dtype=torch.float64, requires_grad=True)
        origin = torch.zeros(3, dtype=torch.float64)
        phi1 = ad_v3d.angle(u, origin, self._x) 
        phi2 = ad_v3d.angle(self._x, origin, v)
        phi = phi1 + phi2
        return phi

    def new_q(self, coord1, coord2, coord3):
        if not self._axes_fixed:
            self.new_compute_axes(coord1,coord2,coord3)
        u = ad_v3d.eAB(coord2, coord1)  # B->A
        v = ad_v3d.eAB(coord2, coord3)  # B->C
        origin = torch.zeros(3, dtype=torch.float64)
        phi1 = ad_v3d.angle(u, origin, self._x) 
        phi2 = ad_v3d.angle(self._x, origin, v)
        phi = phi1 + phi2
        return phi

    def new_compute_axes(self, coord1,coord2,coord3):
        u = ad_v3d.eAB(coord2, coord1)  # B->A
        v = ad_v3d.eAB(coord2, coord3)  # B->C

        if ad_v3d.are_parallel_or_antiparallel(u,v):
            self._bendType = "LINEAR"

        if self._bendType == "REGULAR":                   # not a linear-bend type
            self._w = ad_v3d.normalize(ad_v3d.cross(u,v)) # cross product and normalize
            self._x = ad_v3d.normalize(u + v)             # angle bisector
            return

        #tv1 = torch.tensor([1,0,0], dtype=torch.float64, requires_grad=True) 
        tv1 = torch.tensor([1,0,0], dtype=torch.float64) 
        #tmp_tv2 = torch.tensor([0,1,1], dtype=torch.float64, requires_grad=True)
        tmp_tv2 = torch.tensor([0,1,1], dtype=torch.float64)
        tv2 = ad_v3d.normalize(tmp_tv2)

        u_tv1 = ad_v3d.are_parallel_or_antiparallel(u, tv1)
        v_tv1 = ad_v3d.are_parallel_or_antiparallel(v, tv1)
        u_tv2 = ad_v3d.are_parallel_or_antiparallel(u, tv2)
        v_tv2 = ad_v3d.are_parallel_or_antiparallel(v, tv2)

        # handle both types of linear bends
        if not ad_v3d.are_parallel_or_antiparallel(u, v):
            self._w = ad_v3d.normalize(ad_v3d.cross(u, v))  # orthogonal vector
            self._x = ad_v3d.normalize(u + v)
        # u || v but not || to tv1.
        elif not u_tv1 and not v_tv1:
            self._w = ad_v3d.normalize(ad_v3d.cross(u, tv1))
            self._x = ad_v3d.normalize(ad_v3d.cross(self._w, u))
        # u || v but not || to tv2.
        elif not u_tv2 and not v_tv2:
            self._w = ad_v3d.normalize(ad_v3d.cross(u,tv2))
            self._x = ad_v3d.normalize(ad_v3d.cross(self._w, u))

        if self._bendType == "COMPLEMENT":
            w2 = torch.copy(self._w)
            self._w = -1.0 * self._x  # -w_normal -> x_complement
            self._x = w2
        return
          

class TORS(object):
    def __init__(self, a, b, c, d):

        if a < d: self.atoms = (a, b, c, d)
        else: self.atoms = (d, c, b, a)
        self.A = self.atoms[0]
        self.B = self.atoms[1]
        self.C = self.atoms[2]
        self.D = self.atoms[3]
        self._near180 = 0

    def q(self, geom):
        try:
            tau = ad_v3d.tors(geom[self.A], geom[self.B], geom[self.C], geom[self.D])
        except: 
            raise Exception("Tors.q: unable to compute torsion value")
        return tau

    def new_q(self, coord1, coord2, coord3, coord4):
        try:
            tau = ad_v3d.tors(coord1, coord2, coord3, coord4)
        except: 
            raise Exception("Tors.q: unable to compute torsion value")
        return tau


