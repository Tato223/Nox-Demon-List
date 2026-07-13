const signup_form = document.querySelector(".signup-container__form");

signup_form.addEventListener("submit", async (event) => {
    event.preventDefault();

    try {
        const endPoint = "http://127.0.0.1:8000/register";
        const request = {
            email: signup_form.querySelector("#email")?.value,
            username: signup_form.querySelector("#username")?.value,
            password: signup_form.querySelector("#password")?.value
        }

        const response = await fetch(endPoint, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(request),
        }); 

        if (!response.ok) {
        throw new Error(`HTTP error! Response code: ${response.status}`);
        }

        console.log("Successfully registered!")
    }

    catch (error) {
        console.error("Fetch failed!", error);
    }
});