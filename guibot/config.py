# Copyright 2013-2018 Intranet AG and contributors
#
# guibot is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# guibot is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with guibot.  If not, see <http://www.gnu.org/licenses/>.

"""

SUMMARY
------------------------------------------------------
Global and local (per target or region instance) configuration.


INTERFACE
------------------------------------------------------

"""

import logging

from guibot.errors import UninitializedBackendError, UnsupportedBackendError

log = logging.getLogger('guibot.config')


class GlobalConfig:
    """
    Metaclass used for the definition of static properties (the settings).

    We overwrite the name of the class in order to avoid documenting
    all settings here and adding an empty actual class. Instead, the resulting
    documentation contains just the config class (using this as metaclass)
    and all settings respectively. In this way the front user should not worry
    about such implementation detail and simply use the provided properties.

    For those that like to think about it nonetheless: All methods of the
    resulting config class are therefore static since they are methods of
    a class object, i.e. a metaclass instance.
    """

    # operational parameters shared between all instances

    # time interval between mouse down and up in a click
    toggle_delay = 0.05
    # time interval after a click (in a double or n-click)
    click_delay = 0.1
    # timeout before drag operation
    drag_delay = 0.5
    # timeout before drop operation
    drop_delay = 0.5
    # timeout before key press operation
    delay_before_keys = 0.2
    # time interval between two consecutively typed keys
    delay_between_keys = 0.1
    # time interval between two image matching attempts (used to reduce overhead on the CPU)
    rescan_speed_on_find = 0.2
    #  whether to wait for animations to complete and match only static (not moving) targets
    wait_for_animations = False
    # whether to move the mouse cursor to a location instantly or smoothly
    smooth_mouse_drag = True
    screen_autoconnect = True
    # whether to preprocess capital and special characters and handle them internally
    preprocess_special_chars = True
    # whether to perform an extra needle dump on matching error
    save_needle_on_error = True
    # logging level similar to the python logging module
    image_logging_level = logging.ERROR
    # relative path of the image logging steps
    image_logging_destination = "imglog"
    # number of digits when enumerating the image logging steps, e.g. value=3 for 001, 002, etc.
    image_logging_step_width = 3
    # quality of the image dumps ranging from 0 for no compression to 9 for maximum compression
    # (used to save space and reduce the disk space needed for image logging)
    image_quality = 3

    # backends shared between all instances
    # Same as :py:func:`GlobalConfig.image_logging_destination` but with
    #
    # :param value: name of the display control backend
    # :raises: :py:class:`ValueError` if value is not among the supported backends
    #
    # Supported backends:
    #    * pyautogui - Windows, Linux, and OS X compatible with both the GUI
    #                  actions and their calls executed on the same machine
    #    * autopy - Windows, Linux, and OS X compatible with both the GUI
    #               actions and their calls executed on the same machine.
    #    * vncdotool - guest OS independent or Linux remote OS with GUI
    #                  actions on a remote machine through vnc and their
    #                  calls on a vnc client machine.
    #    * xdotool - Linux X server compatible with both the GUI
    #                actions and their calls executed on the same machine.
    #    * qemu - guest OS independent with GUI actions on a virtual machine
    #             through Qemu Monitor object (provided by Autotest) and
    #             their calls on the host machine.
    #
    # .. warning:: To use a particular backend you need to satisfy its dependencies,
    #     i.e. the backend has to be installed or you will have unsatisfied imports
    display_control_backend = "pyautogui"
    # name of the computer vision backend
    # Same as :py:func:`GlobalConfig.image_logging_destination` but with
    #
    # :param value: name of the computer vision backend
    #
    # Supported backends:
    #     * autopy - simple bitmap matching provided by AutoPy
    #     * contour - contour matching using overall shape estimation
    #     * template - template matching using correlation coefficients,
    #                  square difference, etc.
    #     * feature - matching using a mixture of feature detection,
    #                 extraction and matching algorithms
    #     * cascade - matching using OpenCV pretrained Haar cascades
    #     * text - text matching using EAST, ERStat, or custom text detection,
    #              followed by Tesseract or Hidden Markov Model OCR
    #     * tempfeat - a mixture of template and feature matching where the
    #                first is used as necessary and the second as sufficient stage
    #     * deep - deep learning matching using convolutional neural network but
    #              customizable to any type of deep neural network
    #     * hybrid - use a composite approach with any of the above methods
    #                as matching steps in a fallback sequence
    #
    # .. warning:: To use a particular backend you need to satisfy its dependencies,
    #     i.e. the backend has to be installed or you will have unsatisfied imports.
    find_backend = "hybrid"
    # name of the contour threshold backend
    contour_threshold_backend = "adaptive"
    # name of the template matching backend
    # Same as :py:func:`GlobalConfig.image_logging_destination` but with
    # :param value: name of the template matching backend
    # Supported backends: autopy, sqdiff, ccorr, ccoeff, sqdiff_normed,
    # ccorr_normed, ccoeff_normed.
    template_match_backend = "ccoeff_normed"
    # name of the feature detection backend
    feature_detect_backend = "ORB"
    feature_extract_backend = "ORB"
    feature_match_backend = "BruteForce-Hamming"
    text_detect_backend = "contours"
    text_ocr_backend = "pytesseract"
    deep_learn_backend = "pytorch"
    hybrid_match_backend = "template"


class TemporaryConfig:
    """
    Proxies a GlobalConfig instance extending it to add context
    support, such that once this context ends the changes to the
    wrapped config object are restored.

    This is useful when we have a global config instance and need to
    change it only for a few operations.

    ::

        >>> print(GlobalConfig.delay_before_drop)
        0.5
        >>> with TemporaryConfig() as cfg:
        ...     cfg.delay_before_drop = 1.3
        ...     print(cfg.delay_before_drop)
        ...     print(GlobalConfig.delay_before_drop)
        ...
        1.3
        1.3
        >>> print(GlobalConfig.delay_before_drop)
        0.5
    """

    def __init__(self):
        """Build a temporary global config."""
        object.__setattr__(self, "_original_values", {})

    def __getattribute__(self, name):
        # fallback to GlobalConfig
        return getattr(GlobalConfig, name)

    def __setattr__(self, name, value):
        original_values = object.__getattribute__(self, "_original_values")
        # store the original value only at the first set operation,
        # so further changes won't overwrite the history
        if name not in original_values:
            original_values[name] = getattr(GlobalConfig, name)
        setattr(GlobalConfig, name, value)

    def __enter__(self):
        # our temporary config object
        return self

    def __exit__(self, *_):
        original_values = object.__getattribute__(self, "_original_values")
        # restore original configuration values
        for name, value in original_values.items():
            setattr(GlobalConfig, name, value)
        # no need to keep the backup once everything has been restored
        original_values.clear()


class LocalConfig:
    """
    Container for the configuration of all display control and
    computer vision backends, responsible for making them behave
    according to the selected parameters as well as for providing
    information about them and the current parameters.
    """

    def __init__(self, configure=True, synchronize=True):
        """
        Build a container for the entire backend configuration.

        :param bool configure: whether to also generate configuration
        :param bool synchronize: whether to also apply configuration

        Available algorithms can be seen in the `algorithms` attribute
        whose keys are the algorithm types and values are the members of
        these types. The algorithm types are shortened as `categories`.

        A parameter can be accessed as follows (example)::

            print(self.params["control"]["vnc_hostname"])
        """
        self.categories = {}
        self.algorithms = {}
        self.params = {}

        self.categories["type"] = "backend_types"
        self.algorithms["backend_types"] = ("cv", "dc")

        if configure:
            self.__configure_backend()
        if synchronize:
            self.__synchronize_backend()

    def __configure_backend(self, backend=None, category="type", reset=False):
        if category != "type":
            raise UnsupportedBackendError("Backend category '%s' is not supported" % category)
        if reset:
            # reset makes no sense here since this is the base configuration
            pass
        if backend is None:
            backend = "cv"
        if backend not in self.algorithms[self.categories[category]]:
            raise UnsupportedBackendError("Backend '%s' is not among the supported ones: "
                                          "%s" % (backend, self.algorithms[self.categories[category]]))

        self.params[category] = {}
        self.params[category]["backend"] = backend

    def configure_backend(self, backend=None, category="type", reset=False):
        """
        Generate configuration dictionary for a given backend.

        :param backend: name of a preselected backend, see `algorithms[category]`
        :type backend: str or None
        :param str category: category for the backend, see `algorithms.keys()`
        :param bool reset: whether to (re)set all parent configurations as well
        :raises: :py:class:`UnsupportedBackendError` if `backend` is not among
                 the supported backends for the category (and is not `None`) or
                 the category is not found
        """
        self.__configure_backend(backend, category, reset)

    def configure(self, reset=True, **kwargs):
        """
        Generate configuration dictionary for all backends.

        :param bool reset: whether to (re)set all parent configurations as well

        If multiple categories are available and just some of them are configured,
        the rest will be reset to defaults. To configure specific category without
        changing others, use :py:func:`configure`.
        """
        self.configure_backend(reset=reset)

    def __synchronize_backend(self, backend=None, category="type", reset=False):
        if category != "type":
            raise UnsupportedBackendError("Backend category '%s' is not supported" % category)
        if reset:
            # reset makes no sense here since this is the base configuration
            pass
        # no backend object to sync to
        backend = "cv" if backend is None else backend
        if backend not in self.algorithms[self.categories[category]]:
            raise UninitializedBackendError("Backend '%s' has not been configured yet" % backend)

    def synchronize_backend(self, backend=None, category="type", reset=False):
        """
        Synchronize a category backend with the equalizer configuration.

        :param backend: name of a preselected backend, see `algorithms[category]`
        :type backend: str or None
        :param str category: category for the backend, see `algorithms.keys()`
        :param bool reset: whether to (re)sync all parent backends as well
        :raises: :py:class:`UnsupportedBackendError` if  the category is not found
        :raises: :py:class:`UninitializedBackendError` if there is no backend object
                 that is configured with and with the required name
        """
        self.__synchronize_backend(backend, category, reset)

    def synchronize(self, *args, reset=True, **kwargs):
        """
        Synchronize all backends with the current configuration dictionary.

        :param bool reset: whether to (re)sync all parent backends as well
        """
        self.synchronize_backend(reset=reset)
