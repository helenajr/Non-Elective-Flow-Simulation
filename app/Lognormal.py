##NEW - Class definining a Lognormal distribution with methods that allow us
# to create a Lognormal distrribution by specifying the mean and standard
# deviation of our data, which then get converted to the mu and sigma values
# needed by SimPy.  To use, create an instance of the class with your mean
# and standard deviation values, and call the sample method on the instance
# whenever you want to sample from the distribution.
# Thanks to Prof Tom Monks, University of Exeter, for this code sample.
# https://medicine.exeter.ac.uk/people/profile/index.php?web_id=Thomas_Monks

import numpy as np
import math

class Lognormal:
    """
    Encapsulates a lognormal distirbution
    """
    def __init__(self, mean, stdev, random_seed=None):
        """
        Params:
        -------
        mean = mean of the lognormal distribution
        stdev = standard dev of the lognormal distribution
        """
        self.rand = np.random.default_rng(seed=random_seed)
        mu, sigma = self.normal_moments_from_lognormal(mean, stdev**2)
        self.mu = mu
        self.sigma = sigma
        
    def normal_moments_from_lognormal(self, m, v):
        '''
        Returns mu and sigma of normal distribution
        underlying a lognormal with mean m and variance v
        source: https://blogs.sas.com/content/iml/2014/06/04/simulate-lognormal
        -data-with-specified-mean-and-variance.html

        Params:
        -------
        m = mean of lognormal distribution
        v = variance of lognormal distribution
                
        Returns:
        -------
        (float, float)
        '''
        phi = math.sqrt(v + m**2)
        mu = math.log(m**2/phi)
        sigma = math.sqrt(math.log(phi**2/m**2))
        return mu, sigma
        
    def sample(self):
        """
        Sample from the normal distribution
        """
        return self.rand.lognormal(self.mu, self.sigma)
    
