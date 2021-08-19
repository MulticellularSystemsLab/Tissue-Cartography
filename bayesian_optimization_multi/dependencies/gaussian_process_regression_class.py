# -*- coding: utf-8 -*-
"""
Created on Wed Jun  9 22:14:09 2021

@author: Nilay
"""

import math
import torch
import gpytorch
import pandas as pd
import matplotlib.pyplot as plt
import math 
import numpy as np
import os
import os.path

class gaussianProcessRegression:
	
	""" Initializion:
			Data_x: Input variable for the GPR
			Data_y: Output variables for the GPR
	
	"""
	def __init__(self, data_x, data_y):
		self.data_x = data_x
		self.data_y = data_y
		
	"""
	Arguements:
		split size : Defines the number of samples in the training dataset
		num_samples: Total number of samples
		
	Operation:
		The function spilts the entire data into training and test datasets
		
	Return:
		training and test datasets convereted into a tensor form
	"""	
	def split_data(self, split_size, num_samples):
		# Splitting the data and convert the datatype to a tensor
		train_x = self.data_x[:split_size,:]
		train_y_all_pc = self.data_y[:split_size,:]
		test_x = self.data_x[split_size:num_samples,:]
		test_y_all_pc = self.data_y[split_size:num_samples,:]
		# returning the training and test datasets
		return train_x, train_y_all_pc, test_x, test_y_all_pc
	
	
	"""
	Training the GP models:
		A) GPyTorch was used to fit a GP with RBF Kernel
		B) B) The simplest likelihood for regression is the gpytorch.likelihoods.GaussianLikelihood.
	This assumes a homoskedastic noise model (i.e. all inputs have the same observational noise).
	"""
	def GP_Regressor(self, train_x, train_y_all_pc, test_x, test_y_all_pc, training_iter, fileNameID, ExactGPModel, pc_index):
		"""
		Arguements:
			train_x: training data. Input normalized sampled SE parameters in the screen 
			train_y_all_pc: output training data contains all the PCs (8) for the output shape features. 
			test_x and test_y_all_pc are the correposnding test datasets
			training_iter: Number of iterations for training the GPR model
			fileNameID: Bae of the file that saves the predictions vs true output
			ExactGPModel: A class containing settings (kernel definition and priors) for training a many-one GP model
			pc_index: The principal component for which the model has to be trained and tested
			
			pcIndex
			
		Operations:
			The portion of code fits a gpr on the training data. The later
			section also calculates the error between original output and model predictions
			
		Output:
			The GPR model
			Likelihood of the model
		"""
		# Converting the numpy arrays to torch tensor format
		train_x_t = torch.from_numpy(train_x)
		train_y_t = torch.from_numpy(train_y_all_pc[:,pc_index])
		test_x_t = torch.from_numpy(test_x)
		test_y = test_y_all_pc[:,pc_index]
		
		# initialize likelihood and model		
		likelihood = gpytorch.likelihoods.GaussianLikelihood()
		# Defining models for GPR
		model = ExactGPModel(train_x_t, train_y_t, likelihood)
		# Find optimal model hyperparameters
		model.train()
		likelihood.train()
		# Use the adam optimizer
		optimizer = torch.optim.Adam(model.parameters(), lr=0.1)
		# "Loss" for GPs - the marginal log likelihood
		mll = gpytorch.mlls.ExactMarginalLogLikelihood(likelihood, model)
		# 
		for i in range(training_iter):
			# Zero gradients from previous iteration
			optimizer.zero_grad()
			# Output from model
			output = model(train_x_t)
			# Calc loss and backprop gradients
			loss = -mll(output, train_y_t)
			
			loss.backward()
			print('Iter %d/%d - Loss: %.3f   lengthscale: %.3f   noise: %.3f' % (
					i + 1, training_iter, loss.item(),
					model.covar_module.base_kernel.lengthscale.item(),
					model.likelihood.noise.item()
			))
			optimizer.step()
		
		"""
		Making predictions using the model, calculating errors
		"""
		# Get into evaluation (predictive posterior) mode
		model.eval()
		likelihood.eval()
		# Test points are regularly spaced along [0,1]
		# # Make predictions by feeding model through likelihood
		with torch.no_grad(), gpytorch.settings.fast_pred_var():
			observed_pred = likelihood(model(test_x_t))
			
		with torch.no_grad():
			# Calculating upper and lower bounds of model predictions
			lower, upper = observed_pred.confidence_region()
			# converting upper and lower bound prediction sto numpy array
			lower_numpy = lower.numpy()
			upper_numpy = upper.numpy()
			# Claculating mean prediction
			output_model_predictions = observed_pred.mean.numpy()
			# fetching actual output data
			original_output = test_y
		
		filename = str(fileNameID) + str(pc_index) + ".png"
		# Calculating total error in predictions 
		error_prediction = np.subtract(upper_numpy, lower_numpy)
		# Discretizing coordinate system for updating the parietal_plots
		x_par = np.linspace(np.amin(original_output),np.amax(original_output), num = 100)
		# Plotting the parietal line y = x
		plt.plot(x_par, x_par)
		# Plotting the output predictions against known output value
		plt.plot(original_output, output_model_predictions, 'o', color='black')
		# Plotting the errorbars
		plt.errorbar(original_output, output_model_predictions,
			yerr = error_prediction, lolims = lower_numpy, uplims = upper_numpy, linestyle = "None")
		# Labelling axes
		plt.xlabel(" True output")
		plt.ylabel(" predicted output ")
		# Saving the figure
		plt.savefig("gpr_model_accuracy_plots/" + filename)
		plt.close()
		# returning the gpr modeling
		return model, likelihood
		
		
