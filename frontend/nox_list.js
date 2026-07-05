const levels_container = document.querySelector(".levels-container");

async function fetchData() {
  try {
    const response = await fetch("http://127.0.0.1:8000/levels");

    if (!response.ok) {
      throw new Error(`HTTP error! Response code: ${response.status}`);
    }

    // Create & format necessary elements for each level in database
    const data = await response.json();
    data.data.forEach((level) => {
      const level_element = create_level_element(level);
      const level_anchor = create_level_anchor(level);
      const level_thumb = create_level_embed(level);

      level_anchor.append(level_thumb);
      level_anchor.append(level_element);
      levels_container.append(level_anchor);
    });
  } catch (error) {
    console.error("Fetch failed!", error);
  }
}

function create_level_embed(level) {
  const completion_embed = document.createElement("iframe");
  completion_embed.className = "level__thumb";
  completion_embed.src = get_youtube_embed_url(level.completion_link);
  console.log(completion_embed.src);
  completion_embed.title = "YouTube video player";
  completion_embed.height = 560;
  completion_embed.width = 315;
  completion_embed.allow =
    "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture";
  completion_embed.allowFullscreen = true;

  return completion_embed;
}

function create_level_anchor(level) {
  const level_anchor = document.createElement("a");
  level_anchor.className = "level";
  level_anchor.href = level.completion_link;
  level_anchor.target = "_blank";

  return level_anchor;
}

function create_level_element(level) {
  const level_div = document.createElement("div");
  level_div.className = "level__details";

  const level_title = document.createElement("h2");
  level_title.textContent = `#${level.list_position} - ${level.level_name}`;

  const level_creator = document.createElement("h3");
  level_creator.textContent = `by ${level.creator}`;

  const victor_text = document.createElement("h4");
  victor_text.textContent = `First completed by ${level.first_victor}`;

  const victor_name = document.createElement("span");
  victor_name.className = "victor";

  level_div.append(level_title);
  level_div.append(level_creator);
  level_div.append(victor_text);

  victor_text.append(victor_name);

  return level_div;
}

// Takes youtube link from database and converts to embed link
function get_youtube_embed_url(link) {
  try {
    const url = new URL(link);
    const video_id =
      url.hostname === "youtu.be"
        ? url.pathname.slice(1)
        : url.searchParams.get("v");
    return `https://www.youtube.com/embed/${video_id}`;
  } catch {
    return null;
  }
}

fetchData();
