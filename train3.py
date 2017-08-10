from keras import applications
from keras.preprocessing.image import ImageDataGenerator
from keras import optimizers
from keras.callbacks import CSVLogger, EarlyStopping, ModelCheckpoint, TensorBoard
from keras.models import Model
from keras.layers import Dense, GlobalAveragePooling2D

# based on
# https://www.kaggle.com/ogurtsov/0-99-with-r-and-keras-inception-v3-fine-tune/code

# Settings

train_directory = 'data/train'
validation_directory = 'data/validation'

img_width, img_height = 299, 299
batch_size = 32
train_epochs = 20
fine_tune_epochs = 40
train_samples = 3064
validation_samples = 400

# Data generators & augmentation

datagen = ImageDataGenerator(
    rotation_range=20,
    width_shift_range=0.2,
    height_shift_range=0.2,
    horizontal_flip=True)

train_generator = datagen.flow_from_directory(
    train_directory,
    target_size=(img_height, img_width),
    color_mode='rgb',
    class_mode='binary',
    batch_size=batch_size,
    shuffle=True,
    seed=123)

validation_generator = datagen.flow_from_directory(
    validation_directory,
    target_size=(img_height, img_width),
    color_mode='rgb',
    classes=None,
    class_mode='binary',
    batch_size=batch_size,
    shuffle=True,
    seed=123)

# Loading pre-trained model and adding custom layers

base_model = applications.InceptionV3(weights='imagenet',
                                      include_top=False,
                                      input_shape=(img_height, img_width, 3))
print('Model loaded.')

# Custom layers
x = base_model.output
x = GlobalAveragePooling2D()(x)
x = Dense(1024, activation='relu')(x)
predictions = Dense(1, activation='sigmoid')(x)
model = Model(inputs=base_model.input, outputs=predictions)

for layer in base_model.layers:
    layer.trainable = False

model.compile(
    loss='binary_crossentropy',
    optimizer=optimizers.RMSprop(lr=0.001),
    metrics=['accuracy'])

# train the model on the new data for a few epochs
tensorboard = TensorBoard(
    log_dir='./output/logs/training',
    histogram_freq=1,
    write_graph=True,
    write_images=True)

model.fit_generator(
    train_generator,
    steps_per_epoch=train_samples // batch_size,
    epochs=train_epochs,
    validation_data=validation_generator,
    validation_steps=validation_samples // batch_size,
    verbose=1,
    callbacks=[tensorboard])

for layer in model.layers[:249]:
    layer.trainable = False
for layer in model.layers[249:]:
    layer.trainable = True

model.compile(
    loss='binary_crossentropy',
    optimizer=optimizers.SGD(lr=0.0001, momentum=0.9, decay=1e-5),
    metrics=['accuracy'])

csv_logger = CSVLogger('./output/logs/training.csv', separator=';')

checkpointer = ModelCheckpoint(
    filepath='./output/checkpoints/inceptionV3_{epoch:02d}_{val_acc:.2f}.h5',
    verbose=1,
    save_best_only=True)

early_stopper = EarlyStopping(patience=10)

tensorboard = TensorBoard(
    log_dir='./output/logs/fine_tuning',
    histogram_freq=1,
    write_graph=True,
    write_images=True)

model.fit_generator(
    train_generator,
    steps_per_epoch=train_samples // batch_size,
    epochs=fine_tune_epochs,
    validation_data=validation_generator,
    validation_steps=validation_samples // batch_size,
    verbose=1,
    callbacks=[csv_logger, checkpointer, early_stopper, tensorboard])

model.save_weights('./output/inceptionV3_60epochs.h5')

# serialize model to JSON
model_json = model.to_json()
with open('./output/inceptionV3_40epochs.h5', 'w') as json_file:
    json_file.write(model_json)
