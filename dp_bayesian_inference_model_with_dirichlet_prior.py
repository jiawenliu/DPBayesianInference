import numpy
import matplotlib.pyplot as plt
from copy import deepcopy
import random
import math
import scipy
from scipy.stats import beta
from fractions import Fraction
import operator
import time




def multibeta_function(alphas):
	numerator = 1.0
	denominator = 0.0
	for alpha in alphas:
		numerator = numerator * math.gamma(alpha)
		denominator = denominator + alpha
	# print numerator / math.gamma(denominator)
	return numerator / math.gamma(denominator)

def optimized_multibeta_function(alphas):
	denominator = -1.0
	nominators = []
	denominators = []
	r = 1.0
	for alpha in alphas:
		denominator = denominator + alpha
	for alpha in alphas:
		temp = alpha - 1
		while temp > 0.0:
			nominators.append(temp)
			temp -=1
		if temp < 0.0:
			nominators.append(math.gamma(1 + temp))
	while denominator > 0.0:
		denominators.append(denominator)
		denominator -= 1
	if denominator < 0.0:
		denominators.append(math.gamma(1 + denominator))
	# print nominators
	# print denominators
	d_pointer = len(denominators) - 1
	n_pointer = len(nominators) - 1
	while d_pointer >= 0 and n_pointer >= 0:
		# print nominators[n_pointer],denominators[d_pointer]
		r *= nominators[n_pointer] / denominators[d_pointer]
		n_pointer -= 1
		d_pointer -= 1
	while d_pointer >= 0:
		# print n_pointer,denominators[d_pointer]
		r *= 1.0 / denominators[d_pointer]
		d_pointer -= 1
	while n_pointer >= 0:
		# print nominators[n_pointer] ,d_pointer
		r *= nominators[n_pointer] 
		n_pointer -= 1

	return r

def Hellinger_Distance_Dir(Dir1, Dir2):
	return math.sqrt(1 - multibeta_function((numpy.array(Dir1._alphas) + numpy.array(Dir2._alphas)) / 2.0)/ \
		math.sqrt(multibeta_function(Dir1._alphas) * multibeta_function(Dir2._alphas)))

def Optimized_Hellinger_Distance_Dir(Dir1, Dir2):
	return math.sqrt(1 - optimized_multibeta_function((numpy.array(Dir1._alphas) + numpy.array(Dir2._alphas)) / 2.0)/ \
		math.sqrt(optimized_multibeta_function(Dir1._alphas) * optimized_multibeta_function(Dir2._alphas)))


class Dir(object):
	def __init__(self, alphas):
		self._alphas = alphas
		self._size = len(alphas)

	def __sub__(self, other):
		return Optimized_Hellinger_Distance_Dir(self, other)

	def __add__(self, other):
		return Dir(list(numpy.array(self._alphas) + numpy.array(other._alphas)))

	def show(self):
		print "Dirichlet("+str(self._alphas) + ")"

	def _hellinger_sensitivity(self, r):
		LS = 0.0
		temp = deepcopy(r._alphas)
		for i in range(0, r._size):
			temp[i] += 1
			for j in range(i + 1, r._size):
				temp[j] -= 1
				LS = max(LS, abs((r - self) - (Dir(temp) - self )))
				# print r._alphas,self._alphas,temp,(r-self),(Dir(temp) - self)
				temp[j] += 1
			temp[i] -= 1
		return LS

	def _score_sensitivity(self, r):
		LS = 0.0
		temp = deepcopy(self._alphas)
		for i in range(0, self._size):
			temp[i] += 1
			for j in range(i + 1, self._size):
				temp[j] -= 1
				LS = max(LS, abs(-(r - self) + (r - Dir(temp))))
				temp[j] += 1
			temp[i] -= 1
		return LS


class BayesInferwithDirPrior(object):
	def __init__(self, prior, sample_size, epsilon):
		self._prior = prior
		self._sample_size = sample_size
		self._epsilon = epsilon
		self._bias = numpy.random.dirichlet(self._prior._alphas)
		self._observation = numpy.random.multinomial(1, self._bias, self._sample_size)
		self._observation_counts = numpy.sum(self._observation, 0)
		self._posterior = Dir(self._observation_counts) + self._prior
		self._laplaced_posterior = self._posterior
		self._randomized_posterior = self._posterior
		self._randomized_observation = deepcopy(self._observation)
		self._exponential_posterior = self._posterior
		self._candidate_scores = {}
		self._candidates = []
		self._GS = 0.0
		self._LS = {}
		self._VS = {}
		self._LS_max = 0.0
		self._candidate_VS_scores = {}
		self._accuracy = {"Laplace Mechanism":[],"Randomize Response":[],"Exponential Mechanism":[]}
		self._average = {"Laplace Mechanism":[],"Randomize Response":[],"Exponential Mechanism":[]}
		self._accuracy_expomech = {"Exponential Mechanism with Local Sensitivity":[],"Laplace Mechanism":[], "Exponential Mechanism with Varying Sensitivity":[], "Exponential Mechanism with Global Sensitivity":[]}		
	
	def _set_bias(self, bias):
		self._bias = bias
		self._update_observation()

	def _update_observation(self):
		self._observation = numpy.random.multinomial(1, self._bias, self._sample_size)
		self._posterior = Dir(self._observation_counts) + self._prior

	def _set_candidate_scores(self):
		print "Calculating Candidates and Scores....."
		start = time.clock()
		self._set_candidates([], numpy.sum(self._observation))
		for r in self._candidates:
			self._candidate_scores[r] = -(self._posterior - r)
		print str(time.clock() - start) + " seconds."

	def _set_candidates(self, current, rest):
		if len(current) == len(self._prior._alphas) - 1:
			current.append(rest)
			self._candidates.append(Dir(deepcopy(current)) + self._prior)
			current.pop()
			return
		for i in range(0, rest + 1):
			current.append(i)
			self._set_candidates(current, rest - i)
			current.pop()

	def _set_LS(self):
		for r in self._candidates:
			self._LS[r] = r._hellinger_sensitivity(self._posterior)
			self._LS_max = max(self._LS_max, self._LS[r])

	def _set_LS_max(self):
		self._LS_max = self._posterior._hellinger_sensitivity(self._posterior)


	def _set_GS(self):
		self._GS = Dir([1,1,1,2]) - Dir([1,2,1,1])

	def _set_VS(self):
		t = 2 * math.log(len(self._candidates) / 0.8) / self._epsilon
		print "Calculating Varying Sensitivity Scores....."
		start = time.clock()
		print t
		for r in self._candidates:
			self._LS[r] = r._hellinger_sensitivity(r)
		for r in self._candidates:
			self._candidate_VS_scores[r] = -max([((-self._candidate_scores[r] + t * self._LS[r] - (-self._candidate_scores[i] + t * self._LS[i]))/(self._LS[r] + self._LS[i])) for i in self._candidates])
		print str(time.clock() - start) + "seconds."

	def _almost_randomize(self):
		return

	def _laplace_noize(self):
		self._laplaced_posterior = Dir([alpha + abs(numpy.random.laplace(0, len(self._prior._alphas) * 1.0/self._epsilon)) for alpha in self._posterior._alphas])

	def _laplace_noize_mle(self):
		while True:
			flage = True
			self._laplaced_posterior = Dir([alpha + round(numpy.random.laplace(0, 2.0/self._epsilon)) for alpha in self._posterior._alphas])
			self._laplaced_posterior._alphas[0] += (sum(self._prior._alphas) + self._sample_size - sum(self._laplaced_posterior._alphas))
			for  alpha in self._laplaced_posterior._alphas:
				if alpha < 0.0:
					flage = False
			if flage:
				break

	def _exponentialize_GS(self):
		probabilities = {}
		nomalizer = 0.0
		for r in self._candidates:
			probabilities[r] = math.exp(self._epsilon * self._candidate_scores[r]/(self._GS))
			nomalizer += probabilities[r]
		outpro = random.random()
		for r in self._candidates:
			if outpro < 0:
				return
			outpro = outpro - probabilities[r]/nomalizer
			self._exponential_posterior = r

	def _exponentialize_LS(self):
		probabilities = {}
		nomalizer = 0.0
		for r in self._candidates:
			probabilities[r] = math.exp(self._epsilon * self._candidate_scores[r]/(self._LS_max))
			nomalizer += probabilities[r]
		outpro = random.random()
		for r in self._candidates:
			if outpro < 0:
				return
			outpro = outpro - probabilities[r]/nomalizer
			self._exponential_posterior = r

	def _exponentialize_VS(self):
		probabilities = {}
		nomalizer = 0.0
		for r in self._candidates:
			probabilities[r] = math.exp(self._epsilon * self._candidate_VS_scores[r]/(1.0))
			nomalizer += probabilities[r]
		outpro = random.random()
		for r in self._candidates:
			if outpro < 0:
				return
			outpro = outpro - probabilities[r]/nomalizer
			self._exponential_posterior = r


	def _update_expomech(self, times):
		self._set_candidate_scores()
		self._set_GS()
		self._set_LS_max()
		self._set_VS()
		self._show_all()
		for i in range(times):
			self._exponentialize_LS()
			self._accuracy_expomech["Exponential Mechanism with Local Sensitivity"].append(self._posterior - self._exponential_posterior)
			self._exponentialize_VS()
			self._accuracy_expomech["Exponential Mechanism with Varying Sensitivity"].append(self._posterior - self._exponential_posterior)
			self._exponentialize_GS()
			self._accuracy_expomech["Exponential Mechanism with Global Sensitivity"].append(self._posterior - self._exponential_posterior)
			self._laplace_noize_mle()
			self._show_exponential()
			self._show_laplaced()
			self._accuracy_expomech["Laplace Mechanism"].append(self._posterior - self._laplaced_posterior)
			for key,item in self._accuracy.items():
				self._average[key].append(numpy.mean(item))

	def _update_accuracy(self, times):
		for i in range(times):
			self._randomize()
			self._exponentialize()
			self._laplace_noize()
			self._accuracy["Laplace Mechanism"].append(self._posterior - self._laplaced_posterior)
			self._accuracy["Randomize Response"].append(self._posterior - self._randomized_posterior)
			self._accuracy["Exponential Mechanism"].append(self._posterior - self._exponential_posterior)
			for key,item in self._accuracy.items():
				self._average[key].append(numpy.mean(item))

	def _get_bias(self):
		return self._bias

	def _get_observation(self):
		return self._observation

	def _get_posterior(self):
		return self._posterior


	def _show_bias(self):
		print "The bias generated from the prior distribution is: " + str(self._bias)

	def _show_laplaced(self):
		print "The posterior distribution under Laplace mechanism is: "
		self._laplaced_posterior.show()

	def _show_randomized(self):
		print "The randomized data set is: "
		print self._randomized_observation
		print "The posterior distribution under randomized mechanism is: "
		self._randomized_posterior.show()

	def _show_observation(self):
		print "The observed data set is: "
		print self._observation
		print "The observed counting data is: "
		print self._observation_counts

	def _show_VS(self):
		print "The varying sensitivity for every candidate is:"
		for r in self._candidates:
			print r._alphas, self._VS[r]

	def _show_exponential(self):
		print "The posterior distribution under Exponential Mechanism is: "
		self._exponential_posterior.show()

	def _show_prior(self):
		print "The prior distribution is: "
		self._prior.show()

	def _show_all(self):
		self._show_prior()
		self._show_bias()
		self._show_observation()
		self._show_laplaced()
		self._show_randomized()
		self._show_exponential()
		#self._show_VS()


def draw_error(errors, model):
	plt.subplots(nrows=len(errors), ncols=1, figsize=(12, len(errors) * 5.0))
	plt.tight_layout(pad=2, h_pad=4, w_pad=2, rect=None)
	rows = 1
	for key,item in errors.items():
		plt.subplot(len(errors), 1, rows)
		x = numpy.arange(0, len(item), 1)
		plt.axhline(y=numpy.mean(item), color='r', linestyle = '--', alpha = 0.8, label = "average error",linewidth=3)
		plt.scatter(x, numpy.array(item), s = 40, c = 'b', marker = 'o', alpha = 0.7, edgecolors='white', label = " error")
		plt.ylabel('Hellinger Distance')
		plt.xlabel('Runs (Bias = ' + str(model._bias) + ', GS = ' + str(model._GS) + ', max LS = ' + str(model._LS_max) + ')')
		plt.title(key + ' (Data Size = ' + str(model._sample_size) + ', Global epsilon = ' + str(model._epsilon) + ')')
		plt.legend(loc="best")
		rows = rows + 1
		plt.ylim(-0.1,1.0)
		plt.xlim(0.0,len(item)*1.0)
		plt.grid()
	plt.savefig("dirichlet-GS-VS-LS-size50order3runs100.png")
	return


if __name__ == "__main__":
	# Tests the functioning of the module

	sample_size = 200
	epsilon = 0.8
	prior = Dir([7, 4, 3])
	Bayesian_Model = BayesInferwithDirPrior(prior, sample_size, epsilon)

	Bayesian_Model._update_expomech(100)

	draw_error(Bayesian_Model._accuracy_expomech,Bayesian_Model)
