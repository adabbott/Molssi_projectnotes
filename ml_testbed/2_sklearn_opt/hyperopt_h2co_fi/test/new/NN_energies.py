from sklearn.preprocessing import MinMaxScaler, StandardScaler 
from sklearn.decomposition import PCA
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
from sklearn.metrics import mean_squared_error
from sklearn.utils import shuffle

import pandas as pd
import numpy as np

import sys
import os
import json

X = np.loadtxt("Xval.dat") 
y = np.loadtxt("yval.dat").reshape(-1,1)
#y = data.values[:,-1]
y = y - y.min()
y = y * 219474.63
print(y)




dim = X.shape[1]
#Xscaler = MinMaxScaler(feature_range=(0,1))
#yscaler = MinMaxScaler(feature_range=(0,1))
Xscaler = StandardScaler()
yscaler = StandardScaler()
X = Xscaler.fit_transform(X)
y = yscaler.fit_transform(y)


X_train, X_fulltest, y_train, y_fulltest = train_test_split(X, y, train_size = 800, random_state=42)
# 92 with 5000
#X_valid, X_test, y_valid, y_test = train_test_split(X_fulltest, y_fulltest, test_size = 0.90, random_state=42)


from sklearn.neural_network import MLPRegressor

y_train = np.ravel(y_train)

# LBFGS only cares about hidden layers, activation, alpha, tol?, random_state
# does not use validation data either

actual_y = yscaler.inverse_transform(y_fulltest.reshape(-1,1))

#regs = [0.0001, 0.00001, 0.0]
#architectures = [(100,),(100,100),(200,), (200,200)]
#activ = ['tanh', 'relu', 'logistic']
#for j in regs:
#    data = []
#    for i in range(5):
#        for arch in architectures:
#            for a in activ:
#                mlp = MLPRegressor(hidden_layer_sizes=arch,
#                                   activation=a,
#                                   #activation='logistic',
#                                   #activation='relu',
#                                   #alpha = 0.0050,
#                                   alpha = j,
#                                   solver='lbfgs',
#                                   #solver='adam',
#                                   #random_state=1,
#                                   random_state=i,
#                                   tol=1e-15, 
#                                   verbose=True,
#                                   max_iter=50000)
#                                   #n_iter_no_change=10)
#                mlp.fit(X_train,y_train)
#        
#                p = mlp.predict(X_fulltest)
#                predicted_y = yscaler.inverse_transform(p.reshape(-1,1))
#                #rmse = np.sqrt(mean_squared_error(actual_y, predicted_y))
#                mse = mean_squared_error(actual_y, predicted_y)
#                print(mse, arch,a,i,j)
#                #print(rmse, arch,a,i,j)
#                #data.append(rmse)

mlp = MLPRegressor(hidden_layer_sizes=(200,200),
                   activation='tanh',
                   #activation='relu',
                   alpha = 0.00001,
                   #alpha = 0.0,
                   solver='lbfgs',
                   #solver='adam',
                   random_state=1,
                   tol=1e-15, 
                   verbose=True,
                   max_iter=15000)
                   #n_iter_no_change=10)
mlp.fit(X_train,y_train)
p = mlp.predict(X_fulltest)
#predicted_y = p.reshape(-1,1)
predicted_y = yscaler.inverse_transform(p.reshape(-1,1))
#rmse = np.sqrt(mean_squared_error(y_fulltest, predicted_y))
rmse = np.sqrt(mean_squared_error(actual_y, predicted_y))
print(rmse)
print(rmse)


#import GPy
#kernel = GPy.kern.RBF(dim, ARD=True) #TODO add more kernels to hyperopt space
##kernel = GPy.kern.RBF(dim, ARD=False) #TODO add more kernels to hyperopt space
#model = GPy.models.GPRegression(X_train, y_train.reshape(-1,1), kernel=kernel, normalizer=False)
#model.optimize(max_iters=500, messages=False)
#model.optimize_restarts(10, optimizer="bfgs", verbose=True, max_iters=500, messages=False)
#
#p, v1 = model.predict(X_fulltest, full_cov=False) 
#predicted_y = yscaler.inverse_transform(p.reshape(-1,1))
#actual_y = yscaler.inverse_transform(y_fulltest.reshape(-1,1))
#
#rmse = np.sqrt(mean_squared_error(actual_y, predicted_y))
#print('GP result',rmse)

