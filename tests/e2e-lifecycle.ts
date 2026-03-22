/**
 * PSR Full Lifecycle Test
 *
 * Uploads a text sermon through the UI, waits for scoring to complete,
 * validates all expected data, then deletes via API to clean up.
 *
 * Usage:
 *   cp tests/e2e-lifecycle.ts ~/code/work/dev-browser/skills/dev-browser/scripts/psr-lifecycle.ts
 *   cd ~/code/work/dev-browser/skills/dev-browser && npx tsx scripts/psr-lifecycle.ts
 *
 * Cost: ~$0.50 in OpenAI tokens. Duration: ~2-4 minutes.
 */

import { connect, waitForPageLoad } from "@/client.js";
import * as fs from "fs";
import * as path from "path";

const BASE = "https://howwas.church";
const API = "https://psr-functions-dev.azurewebsites.net";
const ENV_PATH = "/home/tylerbtt/code/personal/sermon/.env";
const ADMIN_KEY = process.env.ADMIN_KEY || (() => {
  try {
    return fs.readFileSync(ENV_PATH, "utf-8")
      .split("\n").find(l => l.startsWith("ADMIN_KEY="))?.split("=").slice(1).join("=") || "";
  } catch { return ""; }
})();
const TIMEOUT_MS = 5 * 60 * 1000; // 5 min max wait
const POLL_INTERVAL = 5000;
const TEST_TITLE = `[TEST] Lifecycle ${Date.now()}`;
const TEST_PASTOR = "Charles Spurgeon";

// ~600 words of Spurgeon — enough for meaningful scoring, cheap enough for a test
const SERMON_TEXT = `POWER is the special and peculiar prerogative of God, and God alone. Twice have I heard this, that power belongs unto God. God is God and power belongs to Him. If He delegates a portion of it to His creatures, yet still it is His power. The sun, although he is like a bridegroom coming out of his chamber and rejoices as a strong man to run his race, yet has no power to perform his motions except as God directs him. The stars, although they travel in their orbits and none could stay them, yet have neither might nor force except that which God daily infuses into them.

The tall archangel, near His Throne, who outshines a comet in its blaze, though he is one of those who excel in strength and hearkens to the voice of the commands of God, yet has no might except that which his Maker gives to him. And when we think of man if he has might or power it is so small and insignificant, that we can scarcely call it such.

This exclusive prerogative of God, is to be found in each of the three Persons of the glorious Trinity. The Father has power for by His word were the heavens made and all the host of them. The Son has power for like His Father, He is the Creator of all things. Without Him was not anything made that was made, and by Him all things consist. And the Holy Spirit has power. It is concerning the power of the Holy Spirit that I shall speak this morning.

We shall look at the power of the Holy Spirit in three ways. First, the outward and visible displays of it. Second, the inward and spiritual manifestations of it. And third, the future and expected works thereof.

The Spirit has manifested the omnipotence of His power in creation works. The creation of the heavens above us is said to be the work of God's Spirit. By His Spirit He has garnished the heavens, His hand has formed the crooked serpent. All the stars of Heaven are said to have been placed aloft by the Spirit. He looses the bands of Orion. He binds the sweet influences of the Pleiades and guides Arcturus with his sons.

The power of the Spirit will thus be made clearly present to your souls. Could we have seen that earth all in confusion, we should have said, Who can make a world out of this? The answer would have been, The power of the Spirit can do it. By the simple spreading of His dove-like wings He can make all things come together. Upon that there shall be order where there was nothing but confusion.

Let the Gospel be preached and the Spirit poured out and you will see that it has such power to change the conscience, to ameliorate the conduct, to raise the debased, to chastise and to curb the wickedness of the race, that you must glory in it. There is nothing like the power of the Spirit. Only let that come and indeed everything can be accomplished.

Go to your Sunday-School. Go to your tract distribution. Go to your missionary enterprise with the conviction that the power of the Spirit is our great help. Rest on the blood of Jesus and your soul is safe, not only now, but throughout eternity. God bless you, my Hearers. Amen.`;

interface StepResult { name: string; ok: boolean; detail: string }
const steps: StepResult[] = [];
let sermonId: string | null = null;

function step(name: string, ok: boolean, detail: string) {
  steps.push({ name, ok, detail });
  console.log(`${ok ? "✅" : "❌"} ${name}: ${detail}`);
}

async function cleanup() {
  if (!sermonId) return;
  console.log(`\n🧹 Cleaning up sermon ${sermonId.substring(0, 8)}...`);
  try {
    const resp = await fetch(`${API}/api/sermons/${sermonId}`, {
      method: "DELETE",
      headers: { "x-admin-key": ADMIN_KEY },
    });
    if (resp.ok) {
      // Verify it's gone
      const check = await fetch(`${API}/api/sermons/${sermonId}`);
      if (check.status === 404) {
        step("Cleanup: sermon deleted", true, "Deleted and verified 404");
      } else {
        step("Cleanup: sermon deleted", false, `Delete returned ${resp.status} but sermon still exists`);
      }
    } else {
      step("Cleanup: sermon deleted", false, `DELETE returned ${resp.status}`);
    }
  } catch (e) {
    step("Cleanup: sermon deleted", false, String(e));
  }
}

// ── Main ──

const client = await connect();
const page = await client.page("lifecycle", { viewport: { width: 1920, height: 1080 } });

try {
  // 1. Create a temp .txt file for upload
  const tmpFile = "/tmp/psr-lifecycle-test.txt";
  fs.writeFileSync(tmpFile, SERMON_TEXT);
  step("Create test file", true, `${SERMON_TEXT.split(/\s+/).length} words written to ${tmpFile}`);

  // 2. Navigate to upload page
  await page.goto(`${BASE}/upload`);
  await waitForPageLoad(page);
  const uploadText = await page.evaluate(() => document.body.innerText);
  if (!uploadText.includes("Drop a file")) throw new Error("Upload page didn't load");
  step("Navigate to upload page", true, "Upload page loaded");

  // 3. Upload the file via the hidden file input
  const fileInput = await page.$("input[type='file']");
  if (!fileInput) throw new Error("File input not found");
  await fileInput.setInputFiles(tmpFile);
  await page.waitForTimeout(1000);

  // Verify file was detected
  const afterUpload = await page.evaluate(() => document.body.innerText);
  if (!afterUpload.includes("psr-lifecycle-test.txt")) throw new Error("File not detected by UI");
  step("Upload file", true, "File detected by UI");

  // 4. Fill in title and pastor
  const titleInput = await page.$("input[aria-label='Sermon title']");
  if (!titleInput) throw new Error("Title input not found");
  await titleInput.fill(TEST_TITLE);

  // Pastor is a <select> — pick "Charles Spurgeon" if available, otherwise use "+ New pastor..."
  const pastorSelect = await page.$("select[aria-label='Pastor name']");
  if (pastorSelect) {
    const options = await pastorSelect.evaluate((el: HTMLSelectElement) =>
      Array.from(el.options).map(o => o.value));
    if (options.includes(TEST_PASTOR)) {
      await pastorSelect.selectOption(TEST_PASTOR);
    } else {
      await pastorSelect.selectOption("__new__");
      await page.waitForTimeout(300);
      const newPastorInput = await page.$("input[aria-label='New pastor name']");
      if (newPastorInput) await newPastorInput.fill(TEST_PASTOR);
    }
  }
  step("Fill metadata", true, `Title: "${TEST_TITLE}", Pastor: "${TEST_PASTOR}"`);

  // 5. Click submit
  const submitBtn = await page.$("button:has-text('Analyze Sermon')");
  if (!submitBtn) throw new Error("Submit button not found");
  await submitBtn.click();
  step("Submit sermon", true, "Clicked Analyze Sermon");

  // 6. Wait for redirect to detail page (should get a sermon ID in URL)
  await page.waitForTimeout(3000);
  const detailUrl = page.url();
  const urlMatch = detailUrl.match(/\/sermons\/([0-9a-f-]{36})/);
  if (!urlMatch) {
    // Check if there's an error on the page
    const errorText = await page.evaluate(() => document.body.innerText);
    const errorLine = errorText.split("\n").find(l => l.toLowerCase().includes("error") || l.toLowerCase().includes("busy"));
    throw new Error(`Not redirected to detail page. URL: ${detailUrl}. Page says: ${errorLine || "unknown"}`);
  }
  sermonId = urlMatch[1];
  step("Redirect to detail", true, `Sermon ID: ${sermonId.substring(0, 8)}...`);

  // 7. Poll API until complete (faster than polling the UI)
  const startTime = Date.now();
  let sermon: any = null;
  while (Date.now() - startTime < TIMEOUT_MS) {
    const resp = await fetch(`${API}/api/sermons/${sermonId}`);
    if (resp.ok) {
      sermon = await resp.json();
      if (sermon.status === "complete") break;
      if (sermon.status === "failed") throw new Error(`Pipeline failed: ${sermon.error || "unknown"}`);
    }
    const elapsed = Math.round((Date.now() - startTime) / 1000);
    process.stdout.write(`\r⏳ Processing... ${elapsed}s`);
    await new Promise(r => setTimeout(r, POLL_INTERVAL));
  }
  console.log(""); // newline after progress
  if (!sermon || sermon.status !== "complete") throw new Error(`Timed out after ${TIMEOUT_MS / 1000}s`);
  const elapsed = Math.round((Date.now() - startTime) / 1000);
  step("Pipeline complete", true, `PSR: ${sermon.compositePsr}, took ${elapsed}s`);

  // 8. Validate composite score
  const psr = sermon.compositePsr;
  if (typeof psr !== "number" || psr < 0 || psr > 100) throw new Error(`Invalid PSR: ${psr}`);
  step("Composite score valid", true, `${psr.toFixed(1)}/100`);

  // 9. Validate all 8 categories present and scored
  const expectedCats = [
    "biblicalAccuracy", "timeInTheWord", "passageFocus", "clarity",
    "engagement", "application", "delivery", "emotionalRange",
  ];
  const cats = sermon.categories || {};
  const missing = expectedCats.filter(c => !cats[c] || typeof cats[c].score !== "number");
  const scored = expectedCats.filter(c => cats[c] && typeof cats[c].score === "number");
  if (missing.length > 0) {
    step("All 8 categories scored", false, `Missing: ${missing.join(", ")}`);
  } else {
    const scores = expectedCats.map(c => `${c.replace(/([A-Z])/g, " $1").trim()}: ${cats[c].score}`);
    step("All 8 categories scored", true, scores.join(", "));
  }

  // 10. Validate each category has reasoning
  const noReasoning = expectedCats.filter(c => cats[c] && !cats[c].reasoning);
  step("All categories have reasoning", noReasoning.length === 0,
    noReasoning.length === 0 ? "All 8 have reasoning" : `Missing reasoning: ${noReasoning.join(", ")}`);

  // 11. Validate sermon type classification
  const validTypes = ["expository", "topical", "survey"];
  step("Sermon type classified", validTypes.includes(sermon.sermonType),
    `Type: ${sermon.sermonType}, confidence: ${sermon.classificationConfidence}%`);

  // 12. Validate transcript present
  const hasTranscript = sermon.transcript?.fullText?.length > 100;
  const hasSegments = sermon.transcript?.segments?.length > 0;
  step("Transcript stored", hasTranscript && hasSegments,
    `${sermon.transcript?.fullText?.length || 0} chars, ${sermon.transcript?.segments?.length || 0} segments`);

  // 13. Validate strengths and improvements
  const hasStrengths = Array.isArray(sermon.strengths) && sermon.strengths.length > 0;
  const hasImprovements = Array.isArray(sermon.improvements) && sermon.improvements.length > 0;
  step("Strengths & improvements", hasStrengths && hasImprovements,
    `${sermon.strengths?.length || 0} strengths, ${sermon.improvements?.length || 0} improvements`);

  // 14. Validate summary
  step("Summary generated", typeof sermon.summary === "string" && sermon.summary.length > 20,
    `${sermon.summary?.length || 0} chars`);

  // 15. Validate enrichment (biblical languages + church history)
  const enrichment = sermon.enrichment;
  step("Enrichment data", enrichment != null,
    enrichment ? `Biblical languages: ${enrichment.biblicalLanguages?.count || 0}, Church history: ${enrichment.churchHistory?.count || 0}` : "Missing");

  // 16. Validate AI detection
  step("AI detection", sermon.aiScore != null && [1, 2, 3].includes(sermon.aiScore),
    `Score: ${sermon.aiScore} (${sermon.aiScore === 1 ? "human" : sermon.aiScore === 2 ? "uncertain" : "AI"})`);

  // 17. Validate sermon content summary
  const cs = sermon.sermonSummary;
  step("Content summary", cs?.overview?.length > 10 && cs?.keyPoints?.length > 0,
    cs ? `Overview: ${cs.overview.length} chars, ${cs.keyPoints.length} key points` : "Missing");

  // 18. Validate pipeline metadata
  step("Pipeline version tracked", !!sermon.pipelineVersion,
    `Version: ${sermon.pipelineVersion || "missing"}`);

  // 19. Validate the detail page renders correctly in the browser
  await page.reload();
  await page.waitForTimeout(5000);
  const detailText = await page.evaluate(() => document.body.innerText);
  const uiChecks = [
    ["/100", "Score gauge"],
    ["Biblical Accuracy", "Category card"],
    [TEST_TITLE.replace("[TEST] ", ""), "Title"],
  ];
  for (const [text, label] of uiChecks) {
    if (!detailText.includes(text as string)) {
      step(`UI: ${label} visible`, false, `"${text}" not found on page`);
    }
  }
  step("UI renders scored sermon", true, "Score gauge, categories, and title visible");

  // 20. Verify sermon appears in list
  await page.goto(`${BASE}/sermons`);
  await page.waitForTimeout(5000);
  const listText = await page.evaluate(() => document.body.innerText);
  step("Sermon in list", listText.includes(TEST_TITLE.replace("[TEST] ", "").substring(0, 20)),
    "Found in sermons list");

} catch (e) {
  step("FATAL", false, String(e).substring(0, 300));
} finally {
  await cleanup();
  await client.disconnect();

  // Summary
  console.log("\n" + "═".repeat(60));
  const passed = steps.filter(s => s.ok).length;
  const failed = steps.filter(s => !s.ok).length;
  console.log(`  ${passed} PASSED, ${failed} FAILED out of ${steps.length}`);
  console.log("═".repeat(60));

  if (failed > 0) {
    console.log("\nFailures:");
    steps.filter(s => !s.ok).forEach(s => console.log(`  ❌ ${s.name}: ${s.detail}`));
    process.exit(1);
  }
}
