## Introduction
This project provides [sonification](https://en.wikipedia.org/wiki/Sonification) of the Tindeq Progressor load cell. It runs a `bokeh` server web application that provides audio and visual feedback for an isometric exercise protocol. It is adapted from Stuart Litlefair's [PyTindeq](https://github.com/StuartLittlefair/PyTindeq) and also uses the `sounddevice` library to generate and play real-time audio, and the `bleak` library to communicate over bluetooth with the Progressor.

## Sonification

**Sonification is the process of mapping data to sound**. When using the Tindeq for strength or rehab protocols, we want to apply a sub-maximal load. This requires some feedback to the user so they know that they are operating near this target load. The official Tindeq app uses a real-time plot of the force data to provide this feedback. Often, looking at a phone screen can be a distraction from performing the exercise. For example, in a finger strength exercise we might want to be actively looking at our hand to ensure the form is correct throughout the duration of the exercise. **By using sound as a cue, the user can focus on the exercise.**

In this app, the user sets a target load, and when a force is applied that falls within a small threshold of this target, a pure tone will be played through the available speakers. If the applied load is outside of this window, white noise is played on top of the pure tone with amplitude proportional to distance from the target. **Pull too much or too little and you'll hear a fuzzy sound.**

## Installation
1. Ensure you have `conda` installed.
2. Clone the repository:
   ```sh
   git clone https://github.com/owenhdiba/tindeq_sonification.git
   ```
3. Move into the newly created directory of the repo. 
4. Create the conda environment:
   ```sh
   conda env create -f environment.yaml
   ```
5. Activate the environment with:
   ```sh
   conda activate tindeq
   ```
## Usage
The exercise protocol involves an active period where load should be applied and audio feedback is played, and a rest period where the sound is turned off and the user should rest. The app cycles through these states for a number of sets. The real-time data is plotted continuously throughout the protocol.

To run the application, with the conda `tindeq` environment activated, use the command: 
```sh
  python main.py
```
This will open a Bokeh web application in your default browser. The application will immediately start scanning for the Tindeq Progressor, so press the button on the device to wake it up. Once connected, the button in the left hand corner will be enabled, allowing the protocol to start. Before starting the protocol, you can alter the work and rest duration, the target load, and the number of sets. Once your ready, click the "Run" button, and after a ten second countdown, the protocol begins.

<p align="center">
  <img
  src="/screenshot.png" width="65%">	
</p>
<p align="center">	
   <em> Example of the web app running.</em>
</p> 
