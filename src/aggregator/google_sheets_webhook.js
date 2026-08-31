/**
 * Google Apps Script — FL-CL Autonomous Experiment Tracker Webhook
 * 
 * Setup Instructions (2 minutes):
 * 1. Open Google Sheets (https://sheets.new)
 * 2. Click Extensions -> Apps Script
 * 3. Delete any code in Code.gs, paste this entire script, and click Save (disk icon)
 * 4. Click Deploy -> New Deployment
 *    - Select type: "Web app"
 *    - Description: "FL-CL Experiment Sync"
 *    - Execute as: "Me"
 *    - Who has access: "Anyone" (allows python to send updates without oauth tokens)
 * 5. Click "Deploy" and copy the "Web app URL" (e.g. https://script.google.com/macros/s/.../exec)
 * 6. Set in your environment or CLI:
 *    export GSHEETS_WEBHOOK_URL="https://script.google.com/macros/s/.../exec"
 */

function doPost(e) {
  var lock = LockService.getScriptLock();
  lock.tryLock(15000);
  
  try {
    var contents = JSON.parse(e.postData.contents);
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var action = contents.action || "round_metric";
    
    if (action === "round_metric") {
      handleRoundMetric(ss, contents);
    } else if (action === "sync_table") {
      handleSyncTable(ss, contents);
    } else if (action === "champion_promotion") {
      handleChampionPromotion(ss, contents);
    }
    
    return ContentService.createTextOutput(JSON.stringify({ status: "success", action: action }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ status: "error", message: err.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  } finally {
    lock.releaseLock();
  }
}

function doGet(e) {
  return ContentService.createTextOutput(JSON.stringify({ status: "active", service: "FL-CL Google Sheets Sync" }))
    .setMimeType(ContentService.MimeType.JSON);
}

// ─────────────────────────────────────────────
// HANDLERS
// ─────────────────────────────────────────────

function handleRoundMetric(ss, contents) {
  var sheetName = contents.sheet || "Live_Rounds";
  var sheet = ss.getSheetByName(sheetName);
  var d = contents.data;
  
  if (!sheet) {
    sheet = ss.insertSheet(sheetName);
    var headers = [
      "Timestamp", "Round", "Loss", "Accuracy (%)", "Macro F1",
      "F1 Normal", "F1 Botnet", "F1 Exfil", "F1 BruteForce", "F1 DoS",
      "Strategy", "Model", "Dataset Rejections"
    ];
    sheet.appendRow(headers);
    formatHeaderRow(sheet, headers.length);
  }
  
  sheet.appendRow([
    new Date(),
    d.round,
    d.loss,
    d.accuracy_pct,
    d.macro_f1,
    d.f1_normal_0,
    d.f1_botnet_1,
    d.f1_exfil_2,
    d.f1_bruteforce_3,
    d.f1_dos_4,
    d.strategy,
    d.model_type,
    d.dataset_rejections
  ]);
}

function handleSyncTable(ss, contents) {
  var sheetName = contents.sheet || "Benchmark_Data";
  var sheet = ss.getSheetByName(sheetName);
  
  if (!sheet) {
    sheet = ss.insertSheet(sheetName);
  } else if (contents.clear !== false) {
    sheet.clear();
  }
  
  var headers = contents.headers || [];
  var rows = contents.rows || [];
  
  if (headers.length > 0) {
    sheet.appendRow(headers);
    formatHeaderRow(sheet, headers.length);
  }
  
  if (rows.length > 0) {
    // Write in batch for high performance
    sheet.getRange(sheet.getLastRow() + 1, 1, rows.length, rows[0].length).setValues(rows);
  }
  
  sheet.autoResizeColumns(1, Math.max(1, headers.length));
}

function handleChampionPromotion(ss, contents) {
  var sheetName = contents.sheet || "Model_Promotions";
  var sheet = ss.getSheetByName(sheetName);
  var d = contents.data;
  
  if (!sheet) {
    sheet = ss.insertSheet(sheetName);
    var headers = [
      "Timestamp", "Round", "Model Backbone", "Gate Passed",
      "F1 Normal", "F1 Botnet", "F1 Exfil", "F1 BruteForce", "F1 DoS", "Reason"
    ];
    sheet.appendRow(headers);
    formatHeaderRow(sheet, headers.length);
  }
  
  var f1 = d.f1_scores || {};
  sheet.appendRow([
    new Date(),
    d.round,
    d.model,
    d.passed ? "PASSED" : "FAILED",
    f1["Normal"] || f1["normal"] || f1["0"] || "-",
    f1["Botnet"] || f1["botnet"] || f1["1"] || "-",
    f1["DNS Exfiltration"] || f1["exfil"] || f1["2"] || "-",
    f1["SSH Brute Force"] || f1["bruteforce"] || f1["3"] || "-",
    f1["DoS"] || f1["dos"] || f1["4"] || "-",
    d.reason || ""
  ]);
}

function formatHeaderRow(sheet, colCount) {
  var headerRange = sheet.getRange(1, 1, 1, colCount);
  headerRange.setFontWeight("bold");
  headerRange.setBackground("#1565C0");
  headerRange.setFontColor("#FFFFFF");
  sheet.setFrozenRows(1);
}
