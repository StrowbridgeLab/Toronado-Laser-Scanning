# Toronado Laser Scanning Program

## Description

This is a set of programs written by Ben Strowbridge (bens@case.edu) to operate a laser scanning microscope. The high-level program, *Toronado*, is written in Python 3 and configures the scanning system. The low-level program, *ToronadoHardware*, is written in VB.NET using Visual Studio 2010 though it should run on any of the more recent Visual Studio versions. The two programs communicate via TCP/IP sockets through an interface that is configured in INI-style text files. 

The core of the *Toronado* program is *DoScan.py* (in *Imaging* folder) which reads a plain text file that configures the scan and indicates which socket to send the resulting raw data. Using *DoScan.py* in a Python terminal, one could operate the entire laser scanning system by editing the plain text configuration file. Users are free to write their own top-level GUI interface that populates the text file entries and then calls *DoScan.py*. A sample top-level GUI written in Python 3 using PyQt5 controls is included in this repository (*Toronado.py* which calls *RasterGUI.py*). Several example image viewers are included in the repository (in the *ImageDisplay* folder). Users also a free to write their own program to receive the raw imaging data via the return TCP/IP socket and display images. The high-level control Python programs only interact with low-level hardware interfaces by passing information through TCP/IP sockets. Because of this, the high-level programs (the text-based "DoScan.py" and the GUI interface, *Toronado.py*) can be run on a different computer ( including Macs and Linux-based machines) from the Windows system that runs the low-level hardware-related code.

While the source code provided is functional, it is not recommended for general use. Many critical parameters, including file locations, are hard-coded within the program for our standardized computer configuration. The *Toronado* program suite assumes the user has access to the direct analog inputs to the XY galvo scanners as well as access to the raw analog output signal from the detector system. A methods paper that describes the operation of these programs is in preparation. A link will be provided here when that paper is available.

## Dependencies

For Toronado (beyond standard Anaconda Python 3.7 system): 

PyQtGraph (http://www.pyqtgraph.org/) <br />
Case Insensitive Dictionary (https://github.com/tivvit/python-case-insensitive-dict) <br />
Tifffile (image file writer, https://pypi.org/project/tifffile/) <br />
Pyperclip (clipboard interface, https://pypi.org/project/pyperclip/)

For ToronadoHardware:

DAQmx acquisition library (National Instruments, tested with version 9.8)  <br />
A NI data acquisition card (PCI-6111 or X series)  <br />
Ionic Zip library (https://www.nuget.org/packages/Ionic.Zip/)

## Contact Information

Ben W. Strowbridge <br />
Dept. of Neurosciences <br />
Case Western Reserve University <br />
Cleveland, Ohio 44106 <br />
bens@case.edu

## License

This work is released under the MIT License.
