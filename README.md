# DecisionsAI

DecisionsAI is an intelligent digital assistant designed to understand and execute various tasks on your computer. It leverages cutting-edge AI technologies to provide voice interaction, automation, and adaptive learning capabilities.

> **IMPORTANT**: This project is currently in an experimental stage and not fully functional. It is actively being developed and updated. Contributions are deeply encouraged and welcome!

![DecisionsAI About](readme/about.png)

> **WARNING**: This project currently requires significant memory resources to run. While optimization efforts are ongoing, including plans to make it compatible with a Raspberry Pi 5, it is currently being developed on an Apple M3 Max with 32GB of RAM. 

> The AI models used in this project collectively consume at least 6GB of memory. Therefore, it is strongly recommended to run DecisionsAI on a machine with a minimum of 16GB of RAM for optimal performance.

> Please note that future updates will focus on reducing the memory footprint and improving efficiency across various hardware configurations and there will be a fallback to smaller models, or API's if the system resources are too low.

<p align="center">
  <img src="readme/example.png" alt="DecisionsAI UI">
</p>


## Vision

Our goal is to create a system assistant that:
- Has context of your system
- Does not get in your way
- Actually accelerates your work

## Features

- Voice-controlled AI assistant
- Task automation and computer control
- Natural language processing
- Text-to-speech and speech-to-text capabilities
- Customizable actions and commands
- Chat interface for text-based interactions
- Multi-model AI support (Ollama, OpenAI, Anthropic)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/DecisionsAI.git
   ```

2. Install dependencies:
   ```bash
   brew install portaudio
   pip install -r requirements.txt
   ```

3. Run the setup script to download the models:
   ```bash
   python setup.py
   ```

## Usage

1. Start the assistant:
   ```bash
   python start.py
   ```

2. Interact with the assistant using voice commands or the chat interface.

## Contributing

We welcome contributions to DecisionsAI! If you have suggestions or improvements, please open an issue or submit a pull request.

## Future Development

This project is a work in progress and will continue to be updated. We aim to make it more robust and powerful, especially when it comes to handling larger projects.

## Other Scripts

Using Open-Interpreter, I've created a little script called `agent` that carries out tasks on your local machine:

```bash
python ./scripts/agent.py
```

When prompted, try entering a command like:
"Create a new text file on my desktop called vegetables.txt and put a list of 15 vegetables in it. Then open the file."

Watch what happens :)

## License

This project is licensed under the CRYSTAL LOGIC (PTY) LTD COMMUNITY LICENSE AGREEMENT. See the [LICENSE.md](LICENSE.md) file for details.
