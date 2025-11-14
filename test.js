const ffmpeg = require("fluent-ffmpeg");
const ffmpegPath = require("ffmpeg-static");
const fs = require("fs");
const path = require("path");

ffmpeg.setFfmpegPath(ffmpegPath);

// === CONFIGURATION ===
const fontPath = "C:/Windows/Fonts/arial.ttf";
const boldFontPath = "C:/Windows/Fonts/arialbd.ttf";

const inputVideo = "input.mp4";
const newAudio = "voice.wav";
const intro = "Intro.mp4";
const outro = "Outro.mp4";

const part1Duration = 2;
const part1Video = "part1.mp4";
const part2Video = "part2.mp4";
const finalPart1 = "final_part1.mp4";
const concatList = "concat_list.txt";
const outputOne = "outputOne.mp4";
const tempVideo = "input-with-text.mp4";
const outputFinal = "output.mp4";

// === STEP 1: Replace First 2s Audio ===
function extractFirstPart() {
  return new Promise((resolve, reject) => {
    ffmpeg(inputVideo)
      .setStartTime(0)
      .setDuration(part1Duration)
      .output(part1Video)
      .on("end", () => {
        console.log("✅ First part extracted.");
        resolve();
      })
      .on("error", reject)
      .run();
  });
}

function replaceAudio() {
  return new Promise((resolve, reject) => {
    ffmpeg()
      .addInput(part1Video)
      .addInput(newAudio)
      .outputOptions(["-c:v copy", "-map 0:v:0", "-map 1:a:0", "-shortest"])
      .output(finalPart1)
      .on("end", () => {
        console.log("✅ Audio replaced in first part.");
        resolve();
      })
      .on("error", reject)
      .run();
  });
}

function extractRemaining() {
  return new Promise((resolve, reject) => {
    ffmpeg(inputVideo)
      .setStartTime(part1Duration)
      .output(part2Video)
      .on("end", () => {
        console.log("✅ Remaining part extracted.");
        resolve();
      })
      .on("error", reject)
      .run();
  });
}

function createConcatFile() {
  return new Promise((resolve, reject) => {
    const content = `file '${path
      .resolve(finalPart1)
      .replace(/\\/g, "/")}'\nfile '${path
      .resolve(part2Video)
      .replace(/\\/g, "/")}'\n`;
    fs.writeFile(concatList, content, (err) => {
      if (err) return reject(err);
      resolve();
    });
  });
}

function mergeParts() {
  return new Promise((resolve, reject) => {
    ffmpeg()
      .input(concatList)
      .inputOptions(["-f", "concat", "-safe", "0"])
      .outputOptions("-c copy")
      .output(outputOne)
      .on("end", () => {
        console.log("✅ Recombined video with replaced audio created.");
        resolve();
      })
      .on("error", reject)
      .run();
  });
}

// === STEP 2: Add Text Overlays ===
const firstBox = [
  "Due date",
  "29-July-2025",
  "G Venkateswara Rao.",
  "42 MG Road, Vijayawada",
  "Rs. ₹999.00",
];

const secondBox = [
  "https://cdma.ap.gov.in/en/vijayawada-municipal-corporation",
  "VMC,GJ66+8RM, Krishnalanka, Vijayawada, Andhra Pradesh 520001",
  "0866 242 2400",
];

const videoWidth = 720;
const videoHeight = 1280;
const fontSize = 26;
const lineSpacing = 60;
const boxY = 930;

function wrapText(text, maxPixelWidth, fontSize) {
  const avgCharWidth = fontSize * 0.6;
  const maxChars = Math.floor(maxPixelWidth / avgCharWidth);
  const result = [];

  if (!text.includes(" ")) {
    for (let i = 0; i < text.length; i += maxChars) {
      result.push(text.slice(i, i + maxChars));
    }
    return result.join("\\n");
  }

  const words = text.split(" ");
  let line = "";

  words.forEach((word) => {
    if ((line + word).length > maxChars) {
      result.push(line.trim());
      line = word + " ";
    } else {
      line += word + " ";
    }
  });

  result.push(line.trim());
  return result.join("\\n");
}

function addStaticTextFilters(lines, yOffset, startTime, duration) {
  const filters = [];
  const endTime = startTime + duration;
  const maxWrapWidth = 600;
  let lineIndex = 0;

  lines.forEach((line) => {
    let customFontSize = fontSize;
    let customX = "w-text_w-40";
    let isBold = /Rs\.|₹/.test(line);

    if (isBold) customFontSize = 48;

    const wrappedLines = wrapText(
      line.replace(/[:\\']/g, "\\$&"),
      maxWrapWidth,
      customFontSize
    ).split("\\n");

    wrappedLines.forEach((wrappedLine) => {
      const yPos = yOffset + lineIndex * lineSpacing;
      filters.push({
        filter: "drawtext",
        options: {
          text: wrappedLine,
          fontfile: isBold ? boldFontPath : fontPath,
          fontsize: customFontSize,
          fontcolor: "black",
          x: customX,
          y: yPos,
          line_spacing: 10,
          box: 1,
          boxborderw: 10,
          shadowcolor: "black",
          shadowx: 1,
          shadowy: 1,
          enable: `between(t,${startTime},${endTime})`,
        },
      });
      lineIndex++;
    });
  });

  return filters;
}

function addTextOverlay() {
  return new Promise((resolve, reject) => {
    const filters = [
      {
        filter: "scale",
        options: {
          width: videoWidth,
          height: videoHeight,
          force_original_aspect_ratio: "decrease",
        },
      },
      {
        filter: "pad",
        options: {
          width: videoWidth,
          height: videoHeight,
          x: "(ow-iw)/2",
          y: "(oh-ih)/2",
          color: "black",
        },
      },
      ...addStaticTextFilters(firstBox, boxY, 12.5, 7.7),
      ...addStaticTextFilters(secondBox, boxY, 21.6, 11.5),
    ];

    ffmpeg(outputOne)
      .videoFilters(filters)
      .outputOptions(["-c:v", "libx264", "-crf", "23", "-preset", "veryfast"])
      .save(tempVideo)
      .on("end", () => {
        console.log("✅ Text overlay added.");
        resolve();
      })
      .on("error", reject);
  });
}

// === STEP 3: Merge Intro, Main, Outro ===
function mergeFinalVideo() {
  return new Promise((resolve, reject) => {
    const command = ffmpeg();
    [intro, tempVideo, outro].forEach((file) => command.input(file));

    command
      .complexFilter([
        "[0:v]scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2,setsar=1[v0]",
        "[1:v]scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2,setsar=1[v1]",
        "[2:v]scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2,setsar=1[v2]",
        "[0:a]aformat=channel_layouts=stereo:sample_rates=44100[a0]",
        "[1:a]aformat=channel_layouts=stereo:sample_rates=44100[a1]",
        "[2:a]aformat=channel_layouts=stereo:sample_rates=44100[a2]",
        "[v0][a0][v1][a1][v2][a2]concat=n=3:v=1:a=1[outv][outa]",
      ])
      .outputOptions(["-map [outv]", "-map [outa]", "-preset", "veryfast"])
      .save(outputFinal)
      .on("start", (cmd) => {
        console.log("🚀 Starting merge with command:");
        console.log(cmd);
      })
      .on("stderr", (line) => {
        console.log("🧠 FFmpeg log:", line);
      })
      .on("end", () => {
        console.log("🎉 Final merged video generated:", outputFinal);
        resolve();
      })
      .on("error", (err) => {
        console.error("❌ Error during final merge:", err.message);
        reject(err);
      });
  });
}

// === Cleanup Temp Files ===
function cleanup() {
  const files = [
    part1Video,
    part2Video,
    finalPart1,
    concatList,
    outputOne,
    tempVideo,
  ];
  files.forEach((file) => {
    if (fs.existsSync(file)) {
      fs.unlinkSync(file);
      console.log(`🧹 Deleted ${file}`);
    }
  });
}

// === MASTER FLOW ===
(async () => {
  try {
    console.log("🎬 Starting video generation...");
    await extractFirstPart();
    await replaceAudio();
    await extractRemaining();
    await createConcatFile();
    await mergeParts();
    await addTextOverlay();
    await mergeFinalVideo();
    cleanup();
  } catch (err) {
    console.error("❌ Error during full process:", err.message);
  }
})();
