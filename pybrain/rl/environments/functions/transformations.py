__author__ = 'Tom Schaul, tom@idsia.ch'


from scipy import rand, dot, power, diag, eye, sqrt, sin, log, exp
from scipy.linalg import orth, norm, inv
from random import shuffle

from function import FunctionEnvironment
from pybrain.structure.parametercontainer import ParameterContainer
from pybrain.rl.environments.fitnessevaluator import FitnessEvaluator


def oppositeFunction(basef):
    """ the opposite of a function """
    if isinstance(basef, FitnessEvaluator):
        if isinstance(basef, FunctionEnvironment):
            res = FunctionEnvironment(basef.xdim, basef.xopt)
        else:
            res = FitnessEvaluator()        
        res.f = lambda x:-basef.f(x)
        if not basef.desiredValue is None:
            res.desiredValue = -basef.desiredValue
        res.toBeMinimized = not basef.toBeMinimized
        return res
    else:    
        return lambda x:-basef(x)
                

class TranslateFunction(FunctionEnvironment):
    """ change the position of the optimum """        
    
    def __init__(self, basef, distance=0.1, offset=None):
        """ by default the offset is random, with a distance of 0.1 to the old one """
        FunctionEnvironment.__init__(self, basef.xdim, basef.xopt)
        if offset == None:
            self._offset = rand(basef.xdim)
            self._offset *= distance / norm(self._offset)
        else:
            self._offset = offset
        self.xopt += self._offset
        self.desiredValue = basef.desiredValue            
        self.toBeMinimized = basef.toBeMinimized
        def tf(x):
            if isinstance(x, ParameterContainer):
                x = x.params
            return basef.f(x - self._offset)
        self.f = tf
    

class RotateFunction(FunctionEnvironment):
    """ make the dimensions non-separable, by applying a matrix transformation to 
    x before it is given to the function """
    
    def __init__(self, basef, rotMat=None):
        """ by default the rotation matrix is random. """
        FunctionEnvironment.__init__(self, basef.xdim, basef.xopt)
        if rotMat == None:
            # make a random orthogonal rotation matrix
            self._M = orth(rand(basef.xdim, basef.xdim))
        else:
            self._M = rotMat
        self.desiredValue = basef.desiredValue            
        self.toBeMinimized = basef.toBeMinimized   
        self.xopt = dot(inv(self._M), self.xopt)
        def rf(x):
            if isinstance(x, ParameterContainer):
                x = x.params
            return basef.f(dot(x, self._M))    
        self.f = rf
        

def penalize(x, distance=5):
    return sum([max(0, abs(xi)-5)**2 for xi in x])
        

class SoftConstrainedFunction(FunctionEnvironment):
    """ Soft constraint handling through a penalization term. """
    
    penalized = True
    
    def __init__(self, basef, distance=5, penalizationFactor=1.):
        FunctionEnvironment.__init__(self, basef.xdim, basef.xopt)
        self.desiredValue = basef.desiredValue            
        self.toBeMinimized = basef.toBeMinimized
        if basef.penalized:
            # already OK
            self.f = basef.f
        else:
            if not self.toBeMinimized:
                penalizationFactor *= -1
                
            def scf(x):
                if isinstance(x, ParameterContainer):
                    x = x.params
                return basef.f(x)+penalize(x, distance)*penalizationFactor
            
            self.f = scf
    
    
def generateDiags(alpha, dim, shuffled=False):    
    diags = [power(alpha, i / (2 * dim - 2.)) for i in range(dim)]
    if shuffled:
        shuffle(diags)
    return diag(diags)


class BBOBTransformationFunction(FunctionEnvironment):
    
    def __init__(self, basef, 
                 translate=True, 
                 rotate=False, 
                 conditioning=None, 
                 asymmetry=None,
                 oscillate=False, 
                 penalize=None,
                 ):
        FunctionEnvironment.__init__(self, basef.xdim, basef.xopt)
        self.desiredValue = basef.desiredValue            
        self.toBeMinimized = basef.toBeMinimized
        
        if translate:            
            self.xopt = (rand(self.xdim) - 0.5) * 9.8
            
        self._diags = eye(self.xdim)            
        self._R = eye(self.xdim)            
        self._Q = eye(self.xdim)            
        
        if conditioning is not None:
            self._diags = generateDiags(conditioning, self.xdim)
        if rotate:
            self._R = orth(rand(basef.xdim, basef.xdim))        
            if conditioning:
                self._Q = orth(rand(basef.xdim, basef.xdim))
                        
        tmp = lambda x: dot(self._Q, dot(self._diags, dot(self._R, x-self.xopt)))
        if asymmetry is not None:
            tmp2 = tmp
            tmp = lambda x: asymmetrify(tmp2(x), asymmetry)
        if oscillate:
            tmp3 = tmp
            tmp = lambda x: oscillatify(tmp3(x))
        
        self.f = lambda x: basef.f(tmp(x))

def asymmetrify(x, beta=0.2):
    res = x.copy()
    dim = len(x)
    for i, xi in enumerate(x):
        if xi > 0:
            res[i] = power(xi, 1+beta*i/(dim-1.)*sqrt(xi))
    return res

def oscillatify(x):
    res = x.copy()
    for i, xi in enumerate(x):
        if xi==0: 
            continue
        elif xi > 0:
            s = 1 
            c1 = 10
            c2 = 7.9
        else:
            s = 1
            c1 = 5.5
            c2 = 3.1
        res[i] = s*exp(log(abs(xi)) + 0.049 * (sin(c1*xi)+sin(c2*xi)))
    return res
