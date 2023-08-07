# Walnut

This is a framework for working with tensors and building, training and analyzing neural networks created using NumPy only. I have provided some examples that explain how to use the framework.

## Overview
Similar to PyTorch I introduced a `Tensor`-object as the central building block that keeps track of its data, gradients and more. However, this framework does not support autograd. Gradients are computed within a network's layer.

```Python
import walnut

a = walnut.Tensor([1, 2, 3])
b = walnut.randn((3,))
c = a + b # addition of tensors
d = a @ b # matrix multiplication of tensors
e = walnut.zeros((5, 5))
```

### Data preprocessing

The framework offers some utility functions, such as `split_train_val_test()` to preprocess data before using it for training.

### Designing a model

Models can be built using a variety of modules, including trainable modules such as linear or convolutional modules. Most of the common activation functions as well as normalization can be applied.

```python
import walnut.nn as nn

model = nn.Sequential([
    nn.layers.Linear(16, input_shape=(4,), act="tanh", init="normal"),
    nn.layers.Linear(16, act="tanh", init="normal"),
    nn.layers.Linear(16, act="tanh", init="normal"),
    nn.layers.Linear(3, act="softmax", init="normal")
])
```

```python
import walnut.nn as nn

model = nn.Sequential([
    nn.layers.Convolution2d(8, input_shape=(1, 28, 28), kernel_size=(3, 3), act="relu", norm="batch", use_bias=False),
    nn.layers.MaxPooling2d(kernel_size=(2, 2)),
    nn.layers.Reshape(),
    nn.layers.Linear(64, act="relu", norm="batch", use_bias=False),
    nn.layers.Linear(10, act="softmax")
])
```

### Training a model

The model can be trained using common algorithms, such as SGD or Adam.

```python
model.compile(
    optimizer=nn.optimizers.SGD(l_r=1e-2, momentum=0.9, nesterov=True),
    loss_fn=nn.losses.Crossentropy(),
    metric=nn.metrics.Accuracy()
)
```

```python
model.compile(
    optimizer=nn.optimizers.Adam(l_r=1e-3),
    loss_fn=nn.losses.Crossentropy(),
    metric=nn.metrics.Accuracy()
)
```

```python
train_loss_hist, val_loss_hist = model.train(x_train, y_train, epochs=10, batch_size=512, val_data=(x_val, y_val))
```

### Analysis

The framework also provides some functions for analyzing a models' parameters and gradients to gain insights (inspired by Andrej Karpathy :) )

```python
activations = {f"{i + 1} {l.__class__.__name__}" : l.y.data.copy() for i, l in enumerate(model.layers) if l.__class__.__name__ == "Tanh"}
nn.analysis.plot_distrbution(activations, title="activation distribution") 
```

![image](https://github.com/DKoflerGIT/NumpyNN/assets/74835806/a205f974-40a6-4d7b-9916-060d4ada9cae)

```python
gradients = {f"{i + 1} {l.__class__.__name__}" : l.y.grad.copy() for i, l in enumerate(model.layers) if l.__class__.__name__ == "Linear"}
nn.analysis.plot_distrbution(gradients, title="gradient distribution")
```

![image](https://github.com/DKoflerGIT/NumpyNN/assets/74835806/8119d55a-fb83-4300-8f9f-5ea1bd8e85d1)


### Experimenting

All modules can also be used individually without a model and their parameters can be inspected. As an example, here is a forward and backward pass for a convolutional layer:
```python
import walnut

X = walnut.randint(shape=(1, 1, 5, 5), low=0, high=10)
W = walnut.randn(shape=(1, 1, 3, 3))
B = walnut.zeros(shape=(1,))
```

```python
import walnut.nn as nn

conv = nn.layers.Convolution2d(out_channels=2)
conv.training = True # tells the layer to define a backward function
conv.w = W
conv.b = B

conv(X)
```

```python
y_grad = walnut.randn(conv.y.shape).data
conv.backward(y_grad)
```

This project is still a work in progress, as I am planning to constantly add new features and optimizations.
The code is not perfect, as I am still learning with every new feature that is added.
If you have any suggestions or find any bugs, please don't hesitate to contact me.