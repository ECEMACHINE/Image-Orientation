import keras
from keras.applications.vgg16 import VGG16
from keras.applications.vgg16 import preprocess_input, decode_predictions
from keras.preprocessing import image
import keras.backend as K

import tensorflow as tf
from tensorflow.python.framework import ops

import numpy as np
import matplotlib.pyplot as plt

from utils import deprocess_image


def load_image(path, target_size=(224, 224)):
    x = image.load_img(path, target_size=target_size)
    x = image.img_to_array(x)
    x = np.expand_dims(x, axis=0)
    x = preprocess_input(x)

    return x


def register_gradient():
    if "GuidedBackProp" not in ops._gradient_registry._registry:
        @ops.RegisterGradient("GuidedBackProp")
        def _GuidedBackProp(op, grad):
            dtype = op.inputs[0].dtype
            return grad * tf.cast(grad > 0., dtype) * \
                tf.cast(op.inputs[0] > 0., dtype)


def modify_backprop(model, name):
    g = tf.get_default_graph()
    with g.gradient_override_map({'Relu': name}):

        # get layers that have an activation
        layer_dict = [layer for layer in model.layers[1:]
                      if hasattr(layer, 'activation')]

        # replace relu activation
        for layer in layer_dict:
            if layer.activation == keras.activations.relu:
                layer.activation = tf.nn.relu

        # re-instanciate a new model
        new_model = VGG16(weights='imagenet')
    return new_model


def guided_backpropagation(img_tensor, model, activation_layer):
    model_input = model.input
    layer_output = model.get_layer(activation_layer).output

    max_output = K.max(layer_output, axis=3)

    get_output = K.function([model_input], [K.gradients(max_output, model_input)[0]])
    saliency = get_output([img_tensor])

    return saliency[0]


if __name__ == "__main__":
    img_width = 224
    img_height = 224

    model = VGG16(weights='imagenet')
    print(model.summary())

    img_path = '/Users/chentao/Desktop/image_orientation_correction-master/WechatIMG14027.jpeg'
    img = load_image(path=img_path, target_size=(img_width, img_height))

    preds = model.predict(img)
    predicted_class = preds.argmax(axis=1)[0]
    # decode the results into a list of tuples (class, description, probability)
    # (one such list for each sample in the batch)
    print("predicted top1 class:", predicted_class)
    print('Predicted:', decode_predictions(preds, top=1)[0])
    # Predicted: [(u'n02504013', u'Indian_elephant', 0.82658225), (u'n01871265', u'tusker', 0.1122357), (u'n02504458', u'African_elephant', 0.061040461)]


    register_gradient()
    guided_model = modify_backprop(model, 'GuidedBackProp')
    gradient = guided_backpropagation(img, guided_model, "block5_pool")

    plt.figure(0)
    plt.imshow(deprocess_image(gradient))
    plt.axis('off')
    plt.show()