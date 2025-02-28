# LooselyCoupled

Simplistic asyncio-based framework for loosely coupling application modules that can interact synchronously and asynchronously (via event queue) 

For instance in smarthome applications, there are different components that need to operate quite independently. One component is responsible for communication over a serial bus like RS232, another component for managing the I2C bus, another component does KNX, another component provides a web frontend to the user, another component acts as a controller with the business logic of the application. In such a scenario, it is beneficial to have quite independent application modules with powerful communication facilities between them: synchronous calls, asynchronous calls and a publish/subscribe mechanism for notifications to possible multiple receivers. I faced such a scenario many years ago when Python3 was still young. I solved the requirement with some code that I have reused many times since then. This project is a reimplementation based on Python's asyncio framework while still supporting non-asyncio code and threading. It provides everything that in my experience is needed all the time for applications with loosely-coupled functionality.

---

## Features

- Manage the lifecycle (from startup to active to shutdown) of independent application modules (implemented as classes).
- Capability to call methods in other modules synchronously.
- Capability to call methods in other modules asynchronously by adding them as tasks into a queue that is getting processed.
- Capability to trigger events that are broadcast asynchronously to all modules subscribing to the event notifications by simply implementing a `on_<eventname>` method.
- Uses a simple addressing scheme for calling methods: `<modulename>.<methodname>`.
- Support of calling asyncio coroutines and regular methods.
- Calling methods and enqueuing tasks and events can be done in a threadsafe manner thus supporting threaded code.
- The event queue supports priorities.
- Facility to react on the event queue becoming empty, i.e. the application becoming idle.
- Contains code for commonly needed stuff like logging, keeping configuration in a yaml configuration file, custom exception handling, and subscribing to signals.
- Example code for often used modules provided, e.g. controller, CherryPy webserver, GPIO management via gpiod with generic support of input and output (incl. blinking).
- Very lightweight due to small and manageable code base.

---

## Installation

Install using PyPi:

```shell
pip3 install looselycoupled
```

<!--
### Package for Debian Linux

Download the provided Debian package (in the desired version) and install it:

```shell
dpkg -i python3-looselycoupled_0.1.0-1_all.deb
```

### Package for Alpine Linux

You may install the Alpine package (https://pkgs.alpinelinux.org/packages?name=py3-looselycoupled) from Alpine's testing repository:

```shell
apk add looselycoupled@testing
```

Note that a line like `@testing https://dl-cdn.alpinelinux.org/alpine/edge/testing` needs to be present in `/etc/apk/repositories` to make the testing repository available.
-->

---

## Quickstart

### Learning by example

Look at the code in the 'example' folder and adapt it as needed. The modules to be used are defined in the provided 'main.py'. You may adapt it to your needs.

### Basic concepts

Modules are created by subclassing "Module" (defined in "module.py"). If you want to create a module that uses separate threads, you may subclass the extended "ModuleThreaded" (defined in "module_threaded.py") that makes it easy.

Modules are managed by an instance of "ModuleManager" that manages the lifecycle of the modules and provides common facilities like the task/event queue, exception handling and logging, and the asyncio event loop. The queue is used for asynchronous calls and event notifications to and between modules.

In each module, three pairs of methods are available for interacting with other modules:

**1. Calling methods of other modules synchronously:**
  - `async def exec_task(self, task, **kwargs)`  
    Coroutine for immediately executing the task `<modulename>.<methodname>` and returning its result.
  - `def exec_task_threadsafe(self, task, **kwargs)`  
    Regular method for doing that; can safely be called from any thread.

**2. Calling methods of other modules asynchronously:**
  - `async def enqueue_task(self, task, **kwargs)`  
    Coroutine for scheduling a call to `<modulename>.<methodname>` by putting it into the execution queue.
  - `def enqueue_task_threadsafe(self, task, **kwargs)`  
    Regular method for doing that; can safely be called from any thread.

**3. Triggering an event that gets notified to any module listening for it by implementing an `on_<eventname>` method:**
  - `async def trigger_event(self, event, **kwargs)`  
    Trigger an event that is put into the execution queue for broadcast.
  - `def trigger_event_threadsafe(self, event=None, **kwargs)`  
    Regular method for doing that; can safely be called from any thread.

---

## Reporting bugs

In case you encounter any bugs, please report the expected behavior and the actual behavior so that the issue can be reproduced and fixed.

---

## Developers

### Clone repository

Clone this repo to your local machine using `https://github.com/towalink/looselycoupled.git`

Install the module temporarily to make it available in your Python installation:
```shell
pip3 install -e <path to root of "src" directory>
```

---

## License

[![License](http://img.shields.io/:license-agpl3-blue.svg?style=flat-square)](https://opensource.org/licenses/AGPL-3.0)

- **[AGPL3 license](https://opensource.org/licenses/AGPL-3.0)**
- Copyright 2025 © <a href="https://github.com/towalink/looselycoupled" target="_blank">Dirk Henrici</a>.
