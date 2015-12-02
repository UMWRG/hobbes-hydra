HydraTools
==========

WaterSys2Hydra
--------------

Conversion tool for WaterSys agents to Hydra templates. 

### Usage:

- Print help message:

  ```
  python WaterSys2Hydra.py [-h]
  ```

- Generate template file from model folder:

  ```
  python WaterSys2Hydra.py FOLDERNAME
  ```

  This will generate a file called `FOLDERNAME.xml`.

- Specify filename:

  ```
  python WaterSys2Hydra.py FOLDERNAME -o output.xml
  ```

  creates `output.xml`.

### Authors:

Adrien Gaudard, Eawag

Philipp Meier, Eawag

### (c) Copyright:
Copyright (c) 2015 Eawag, Swiss Federal Institute of Aquatic Science and Technology

Seestrasse 79, CH-6047 Kastanienbaum, Switzerland

Hydra2WaterSys
--------------

### Usage:

- Print help message:

  ```
  python WaterSys2Hydra.py [-h]
  ```

- Generate a set of agent classes from a template file:

  ```
  python Hydra2WaterSys.py TEMPLATE.xml -o agents_folder
  ```

  For each agent type (nodes, links, networks, and institutions) a separate
  file is created inside `agents_folder`.


### Authors:

Adrien Gaudard, Eawag

Philipp Meier, Eawag

### (c) Copyright:
Copyright (c) 2015 Eawag, Swiss Federal Institute of Aquatic Science and Technology

Seestrasse 79, CH-6047 Kastanienbaum, Switzerland
