# Cubli

Beginnings of a python based program to control a self balancing cube (inspired by [Cubli](https://www.youtube.com/watch?v=n_6p-1J551Y) leveraging reaction wheels (UAV motors in my case) and OTS position encoders on a raspberry pi. Made some progress on control loops and actually had the breadboard hardware working before I realized the update rate of my multi-channel encoder reader was insufficient to command my controller at sufficient frequency. I ultimately put this on hold to pursue my Udacity Robotics Software Engineer Nanodegree.

I'm hoping to return to this project as some point to tweak things and see if python is really capable of executing real-time, multi-threaded controls like this. My guess is not very well, but a hybrid approach using real-time ROS seems like a reasonable solution I'd be excited to try out. Luckily my programming skills have vastly improved since I started this project.
