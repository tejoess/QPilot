const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        AlignmentType, BorderStyle, WidthType, VerticalAlign } = require('docx');
const fs = require('fs');

const metaPath = process.argv[2] || 'meta.json';
const questionsPath = process.argv[3] || 'questions.json';
const meta = JSON.parse(fs.readFileSync(metaPath, 'utf8'));
const { questions } = JSON.parse(fs.readFileSync(questionsPath, 'utf8'));

const qMap = {};
questions.forEach(q => { qMap[q.qid] = q.question; });

const slots = {
  Q1a: qMap[1]  || '', Q1b: qMap[2]  || '', Q1c: qMap[3]  || '',
  Q1d: qMap[4]  || '', Q1e: qMap[5]  || '',
  Q2a: qMap[6]  || '', Q2b: qMap[7]  || '',
  Q3a: qMap[8]  || '', Q3b: qMap[9]  || '',
  Q4a: qMap[10] || '', Q4b: qMap[11] || '',
  Q5a: qMap[12] || '', Q5b: qMap[13] || '',
  Q6a: qMap[14] || '', Q6b: qMap[15] || '',
};

const FONT = "Times New Roman";
const SIZE = 22;
const noBorder = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const noBorders = { top: noBorder, bottom: noBorder, left: noBorder, right: noBorder };
const noMargins = { top: 0, bottom: 60, left: 0, right: 0 };

const COL_Q   = 700;
const COL_SUB = 600;
const COL_MRK = 800;
const COL_TXT = 9746 - COL_Q - COL_SUB - COL_MRK;

function B(text) { return new TextRun({ text, bold: true, font: FONT, size: SIZE }); }
function N(text) { return new TextRun({ text, font: FONT, size: SIZE }); }

function makeCell(runs, width, align = AlignmentType.LEFT) {
  return new TableCell({
    borders: noBorders,
    width: { size: width, type: WidthType.DXA },
    margins: noMargins,
    verticalAlign: VerticalAlign.TOP,
    children: [new Paragraph({ alignment: align, children: runs })]
  });
}

function qRow(qLabel, subLabel, text, marks) {
  return new Table({
    width: { size: 9746, type: WidthType.DXA },
    columnWidths: [COL_Q, COL_SUB, COL_TXT, COL_MRK],
    rows: [new TableRow({ children: [
      makeCell(qLabel   ? [B(qLabel)]   : [N('')], COL_Q),
      makeCell(subLabel ? [B(subLabel)] : [N('')], COL_SUB),
      makeCell([N(text)], COL_TXT),
      makeCell(marks    ? [B(marks)]    : [N('')], COL_MRK, AlignmentType.RIGHT),
    ]})]
  });
}

function spacer() { return new Paragraph({ children: [new TextRun({ text: '', size: SIZE })] }); }
function centered(...runs) { return new Paragraph({ alignment: AlignmentType.CENTER, children: runs }); }
function hrLine() {
  return new Paragraph({
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "000000", space: 1 } },
    children: [new TextRun({ text: '', size: SIZE })]
  });
}

const children = [
  centered(B(`Paper / Subject Code: ${meta.subject_code} / ${meta.subject_name}`)),
  spacer(),
  centered(N(`${meta.date}     Duration: ${meta.duration}     [Max Marks: ${meta.max_marks}]`)),
  centered(N(`QP CODE: ${meta.qp_code}`)),
  spacer(),
  hrLine(),
  spacer(),

  new Paragraph({ children: [B('N.B.: '), N('(1) Question No. 1 is Compulsory.')] }),
  new Paragraph({ children: [N('           (2) Attempt any THREE questions out of the remaining FIVE.')] }),
  new Paragraph({ children: [N('           (3) All questions carry equal marks.')] }),
  new Paragraph({ children: [N('           (4) Assume suitable data, if required and state it clearly.')] }),
  spacer(),
  hrLine(),
  spacer(),

  // Q1 - Attempt any FOUR with 5 sub-questions
  qRow('Q1.', '',    'Attempt any FOUR',  '[20]'),
  qRow('',    'a)',  slots.Q1a,           '[05]'),
  qRow('',    'b)',  slots.Q1b,           '[05]'),
  qRow('',    'c)',  slots.Q1c,           '[05]'),
  qRow('',    'd)',  slots.Q1d,           '[05]'),
  qRow('',    'e)',  slots.Q1e,           '[05]'),
  spacer(),

  // Q2-Q6
  ...['Q2','Q3','Q4','Q5','Q6'].flatMap(q => [
    qRow(`${q}.`, 'a)', slots[`${q}a`], '[10]'),
    qRow('',      'b)', slots[`${q}b`], '[10]'),
    spacer(),
  ]),

  hrLine(),
];

const doc = new Document({
  sections: [{
    properties: {
      page: {
        size: { width: 11906, height: 16838 },
        margin: { top: 1080, right: 1080, bottom: 1080, left: 1080 }
      }
    },
    children
  }]
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync('question_paper.docx', buf);
  console.log('DOCX saved: question_paper.docx');
});