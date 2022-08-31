"""
NiFpga, a thin wrapper around the FPGA Interface C API

Copyright (c) 2015 National Instruments
"""
from .statuscheckedlibrary import (NamedArgtype,
                                   LibraryFunctionInfo,
                                   StatusCheckedLibrary,
                                   LibraryNotFoundError)
import ctypes
from enum import Enum


class DataType(Enum):
    """ DataType is an enumerator, with the intention of abstracting the
    association between datatypes and ctypes within the Python API.
    """
    Bool = 1
    I8 = 2
    U8 = 3
    I16 = 4
    U16 = 5
    I32 = 6
    U32 = 7
    I64 = 8
    U64 = 9
    Sgl = 10
    Dbl = 11
    Fxp = 12
    Cluster = 13

    def __str__(self):
        return self.name

    def _return_ctype(self):
        """ Returns the associated ctype of a given datatype. """
        _datatype_ctype = {
            DataType.Bool: ctypes.c_uint8,
            DataType.I8: ctypes.c_int8,
            DataType.U8: ctypes.c_uint8,
            DataType.I16: ctypes.c_int16,
            DataType.U16: ctypes.c_uint16,
            DataType.I32: ctypes.c_int32,
            DataType.U32: ctypes.c_uint32,
            DataType.I64: ctypes.c_int64,
            DataType.U64: ctypes.c_uint64,
            DataType.Sgl: ctypes.c_float,
            DataType.Dbl: ctypes.c_double,
            DataType.Fxp: ctypes.c_uint32,
            DataType.Cluster: ctypes.c_uint32,
        }
        return _datatype_ctype[self]

    def isSigned(self):
        if self == DataType.I8 \
           or self == DataType.I16 \
           or self == DataType.I32 \
           or self == DataType.I64 \
           or self == DataType.Sgl \
           or self == DataType.Dbl:
            return True
        return False


class FifoPropertyType(Enum):
    """ Types of FIFO Properties, intended to abstract away the C Type. """
    I32 = 1
    U32 = 2
    I64 = 3
    U64 = 4
    Ptr = 5

    def __str__(self):
        return self.name

    def _return_ctype(self):
        """ Returns the associated ctype of a given property type. """
        _propertyType_ctype = {
            FifoPropertyType.I32: ctypes.c_int32,
            FifoPropertyType.U32: ctypes.c_uint32,
            FifoPropertyType.I64: ctypes.c_int64,
            FifoPropertyType.U64: ctypes.c_uint64,
            FifoPropertyType.Ptr: ctypes.c_void_p
        }
        return _propertyType_ctype[self]


class FifoProperty(Enum):
    BytesPerElement = 1  # U32
    BufferAllocationGranularityElements = 2  # U32
    BufferSizeElements = 3  # U64
    MirroredElements = 4  # U64
    DmaBufferType = 5  # I32
    DmaBuffer = 6  # Ptr
    FlowControl = 7  # I32
    ElementsCurrentlyAcquired = 8  # U64
    PreferredNumaNode = 9  # I32

    def __str__(self):
        return self.name


class FlowControl(Enum):
    """ When flow control is disabled, the FIFO no longer acts like a FIFO.
    The FIFO will overwrite data in this mode. The FPGA fully controls when
    data transfers. This can be useful when regenerating a waveform or when
    you only care about the most recent data.
    For Host to Target FIFOs, this only disables flow control when the entire FIFO
    has been written once.
    For Target to Host FIFOs, flow control is disabled on start and the FPGA can
    begin writing then.
    """
    DisableFlowControl = 1
    """ Default FIFO behavior. No data is lost, data only moves when there is
    room for it.
    """
    EnableFlowControl = 2


class DmaBufferType(Enum):
    """ Allocated by RIO means the driver take the other properties and create
    a buffer that meets their requirements.
    """
    AllocatedByRIO = 1
    """ Allocated by User means you will allocate a buffer and set the DMA Buffer
    property with your buffer. The driver will then use this buffer as the
    underlying host memory in the FIFO.
    """
    AllocatedByUser = 2


_fifo_properties_to_types = {
    FifoProperty.BytesPerElement: FifoPropertyType.U32,
    FifoProperty.BufferAllocationGranularityElements: FifoPropertyType.U32,
    FifoProperty.BufferSizeElements: FifoPropertyType.U64,
    FifoProperty.MirroredElements: FifoPropertyType.U64,
    FifoProperty.DmaBufferType: FifoPropertyType.I32,
    FifoProperty.DmaBuffer: FifoPropertyType.Ptr,
    FifoProperty.FlowControl: FifoPropertyType.I32,
    FifoProperty.ElementsCurrentlyAcquired: FifoPropertyType.U64,
    FifoProperty.PreferredNumaNode: FifoPropertyType.I32,
}


class FpgaViState(Enum):
    """ The FPGA VI has either been downloaded and not run, or the VI was aborted
    or reset. """
    NotRunning = 0
    """ An error has occurred. """
    Invalid = 1
    """ The FPGA VI is currently executing. """
    Running = 2
    """ The FPGA VI stopped normally.  This indicates it was not aborted or reset,
    but instead reached the end of any loops it was executing and ended. """
    NaturallyStopped = 3


_SessionType = ctypes.c_uint32
_IrqContextType = ctypes.c_void_p

OPEN_ATTRIBUTE_NO_RUN = 1
OPEN_ATTRIBUTE_BITFILE_PATH_IS_UTF8 = 2
RUN_ATTRIBUTE_WAIT_UNTIL_DONE = 1
CLOSE_ATTRIBUTE_NO_RESET_IF_LAST_SESSION = 1
INFINITE_TIMEOUT = 0xffffffff


class _NiRIO(StatusCheckedLibrary):
    """
    _NiFpga, a thin wrapper around the FPGA Interface C API

    Defines FPGA Interface C API types, and provides the _NiFpga class
    which loads C API symbols and allows them to be called, e.g.
    nifpga.Open(<args>) or nifpga["ReadU32](<args>). If any NiFpga function
    return status is non-zero, the appropriate exception derived from either
    WarningStatus or ErrorStatus is raised.

    While _NiFpga can be used directly, Session provides a higher-level and
    more convenient API that is better-suited for most users.
    """

    def __init__(self):
        library_function_infos = [
            LibraryFunctionInfo(
                pretty_name="Route_Signal",
                name_in_library="niFlexRio_RouteSignal",
                named_argtypes=[
                    NamedArgtype("session", _SessionType),
                    NamedArgtype("source", ctypes.c_char_p),
                    NamedArgtype("destination", ctypes.c_char_p),
                    NamedArgtype("routeTicket", ctypes.POINTER(ctypes.c_int32)),
                ]),
                    ]  # list of function_infos
        
        try:
            super(_NiRIO, self).__init__(library_name="NIFLEXRIOAPI",
                                          library_function_infos=library_function_infos)
        except LibraryNotFoundError as e:
            import platform
            system = platform.system().lower()
            if system == 'windows':
                raise LibraryNotFoundError(
                    "Unable to find NiFpga.dll on your system, "
                    "ensure you have installed the relevent RIO distribution for your device. "
                    "Search for your product here: http://www.ni.com/downloads/ni-drivers/ "
                    "Original Exception: " + str(e))
            if system == 'linux':
                raise LibraryNotFoundError(
                    "Unable to find libNiFpga.so on your system, "
                    "If you are on desktop linux, ensure you have installed the latest "
                    "RIO Linux distribution for your product, such as https://www.ni.com/en-us/support/downloads/drivers/download.ni-linux-device-drivers.html "
                    "If you are on a Linux RT embedded target (cRIO, sbRIO, FlexRIO, Industrial Controller, etc) install NI-RIO to your target "
                    "though MAX following these instructions: https://www.ni.com/getting-started/set-up-hardware/compactrio/controller-software "
                    "Original Exception: " + str(e))
            if system == 'darwin':
                raise LibraryNotFoundError(
                    "Unable to find NiFpga.Framework on your system, "
                    "Sorry we don't yet support using RIO Devices on OSX, contact your sales person "
                    "for the latest information on OSX support. "
                    "Original Exception: " + str(e))
            raise
