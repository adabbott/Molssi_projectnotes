from keras.models import Sequential, Model
#from keras.layers.core import Dense, Input
from keras.layers import Dense, Input, Activation
#from keras.layers.core import Activation
from keras.models import load_model
from keras.optimizers import TFOptimizer
from sklearn.preprocessing import MinMaxScaler, StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
from tensorflow.contrib.opt import ScipyOptimizerInterface
#import tensorflow as tf
#import keras

#from custom_optimizers import ScipyOpt
import pandas as pd
import numpy as np

data = pd.read_csv("PES.dat") 
data = data.drop_duplicates(subset = "E")
X = data.values[:,:-1]
y = data.values[:,-1].reshape(-1,1)
y = y - y.min()
Xscaler = StandardScaler()
yscaler = StandardScaler()
X = Xscaler.fit_transform(X)
y = yscaler.fit_transform(y)
X_train, X_fulltest, y_train, y_fulltest = train_test_split(X, y, test_size = 0.2, random_state=42)
X_valid, X_test, y_valid, y_test = train_test_split(X_fulltest, y_fulltest, test_size = 0.5, random_state=42)
in_dim = tuple([X_train.shape[1]])
out_dim = y_train.shape[1]
valid_set = tuple([X_valid, y_valid])

inputs = Input(shape=in_dim)
x = Dense(64, activation='tanh')(inputs)
x = Dense(64, activation='tanh')(x)
predictions = Dense(1, activation='linear')(x)
model = Model(inputs=inputs, outputs=predictions)

#opt = TFOptimizer(RMSPropOptimizer(0.01))
loss = mean_squared_error(y_train, predictions)
opt = ScipyOptimizerInterface(loss, method="L-BFGS-B")
model.compile(optimizer=opt,
              loss='mse')
model.fit(X_train, y_train, epochs=100)  


#for i in range(1):
#    model = Sequential()
#    model.add(Dense(100, input_dim=in_dim, kernel_initializer='normal'))
#    model.add(Activation('sigmoid'))
#    model.add(Dense(out_dim, kernel_initializer='normal'))
#    model.add(Activation('linear'))
#
#    # fit the model 
#    #opt = ScipyOpt(model=model, x=X_train, y=y_train, nb_epoch=1000)
#    #opt = ScipyOptimizerInterface(loss=prediction, options={'maxit':100})
#
#    #opt = tf.train.AdamOptimizer(0.01)
#    #opt = keras.optimizers.Adam(lr=0.01)
#    loss = keras.losses.mean_squared_error(y_true, y_pred)
#    optimizer = tf.contrib.opt.ScipyOptimizerInterface(loss, method="L-BFGS-B")
#
#    model.compile(loss='mse', optimizer=opt, metrics=['mae'])
#    model.fit(x=X_train,y=y_train,epochs=1000)
#    #model.fit(x=X_train,y=y_train,epochs=1000,batch_size=X_train.shape[0])#validation_data=valid_set,batch_size=5,verbose=2)
#    #models.append(model)
#    #
#    ## analyze the model performance 
#    #p = model.predict(np.array(X_test))
#    #predicted_y = yscaler.inverse_transform(p.reshape(-1,1))
#    #actual_y = yscaler.inverse_transform(y_test.reshape(-1,1))
#    #mae = mean_absolute_error(actual_y, predicted_y) 
#    #rmse = np.sqrt(mean_squared_error(actual_y, predicted_y))
#
#    #RMSE.append(rmse)
#    #MAE.append(mae)
#    print("Done with", i)
#
#print(MAE)
#print(RMSE)
