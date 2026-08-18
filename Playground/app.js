const RIM_URL = "http://127.0.0.1:8000/v1/chat/completions";

const RIM_KEY = "sk-smartllm-PRVzro0VdGNjVS5fa8SnJX5qNHzirl97ZInfur-amqo";

async function sendMessage() {
    const input = document.getElementById("message");
    const message = input.value.trim();

    if (!message) return;

    addMessage("user", message);

    input.value = "";

    try {
        const response = await fetch(RIM_URL, {
            method: "POST",

            headers: {
                "Authorization": `Bearer ${RIM_KEY}`,
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                model: "llama-3.1-8b-instant",

                messages: [
                    {
                        role: "user",
                        content: message
                    }
                ]
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data?.error?.message || "Request failed"
            );
        }

        const answer =
            data.choices[0].message.content;

        addMessage("assistant", answer);

        console.log("Model:", data.model);
        console.log("Usage:", data.usage);

    } catch (error) {

        addMessage(
            "assistant",
            `Error: ${error.message}`
        );
    }
}