## Problem (look_at_cc)

**(a)** Download the WARC file above, or find the copy we provide on the cluster. Let's look at the first page in this file. This is a gzipped file, and you can browse its contents with:
```
$ zcat /data/CC/example.warc.gz | less
```
less lets you browse the file using keyboard arrows, Page Up, Page Down. To exit, press "q". Look at the very first web page. What is its URL? Is it still accessible? Can you tell what the page seems to be about by looking at the raw HTML?

**Answer:** The URL of the first web page is `http://0371rykj.com/ipfhsb/34.html`. The page is still accessible—it redirects to `http://www.0371rykj.com/ipfhsb/34.html`. Based on the page title "甘南实贩装饰工程有限公司" (Gannan Shifan Decoration Engineering Co., Ltd.), the page appears to be about a Chinese decoration/interior design company that sells testing equipment like temperature/humidity chambers.

---

**(b)** Let's now look at the corresponding WET file:
```
$ zcat /data/CC/example.warc.wet.gz | less
```
Note that the WET files contain HTTP headers (e.g., Content-Length) that are not part of the extracted text contents. If you look at the first example, you will see that it contains text that was extracted from the raw HTML you just saw. Notice that much of the extracted text is reminiscent of the HTML structure, and not actually the page's main content. Are there parts of the text you see that you think should have been filtered out by the extractor? Think about the quality of this text as training data: what might go wrong in training a model on text that looks like this? Conversely, what useful information can a model potentially extract from this page?

**Answer:** Yes, several parts of the extracted text should have been filtered out. The text includes explicit adult content keywords in the page title/meta tags (e.g., ""), navigation menus, breadcrumb trails, footer content, and boilerplate UI elements like "查看更多", "在線咨詢", "首頁", etc. Training a model on such text could cause the model to generate spam-like adult keywords, repetitive navigation structures, or fragmented boilerplate content instead of coherent prose. However, the page does contain useful technical specifications for industrial testing equipment (temperature ranges, dimensions, materials), which could be valuable for domain-specific applications.

---

**(c)** What makes a good training example is highly contextual. Describe an application domain for which this example might be useful to have in the training data, and one where it might not be.

**Answer:** This example might be useful for training a model to understand Chinese industrial/technical product specifications or e-commerce pages. It would not be useful for training a general-purpose language model focused on generating high-quality, coherent prose or for safety-critical applications due to the spam/adult content.

---

**(d)** Let's look at some more examples to get a better sense of what's in the Common Crawl. Look through 25 more WET records. For each record, very briefly comment on the document's language (if you can identify it), the domain name, what type of page it is, etc. How many examples does it take until you see what you'd deem a "high-quality" webpage?

**Answer:** Annotations of 25 WET records (after the first page):

1. `buildd.raspbian.org` - English - Build log for Raspbian package (technical, low quality for prose)
2. `cgi.linuxfocus.org` - English - LinuxFocus article about BORG graphics (technical tutorial, **high quality**)
3. `dll.fyicenter.com` - English - DLL file information page (technical reference, boilerplate-heavy)
4. `lists.clir.org` - English - CODE4LIB mailing list archive (forum/list, boilerplate-heavy)
5. `protists.ensembl.org` - English - Ensembl Genomes gene summary page (scientific database, navigation-heavy)
6. `www.htslib.org` - English - samtools manual page (**high quality** technical documentation)
7. `www.le-metayer.fr` - French/English - Unix timestamp converter tool page (utility, minimal content)
8. `7customs.com` - Korean - Customs/shipping tracking page (e-commerce, boilerplate-heavy)
9. `acordes.lacuerda.net` - Spanish - Guitar chords for "Remolino" (music/chords, structured data)
10. `ajedrezelx.blogspot.com` - Spanish - Chess club blog post about tournament results (blog, decent quality)
11. `aprendeaprogramar.com` - Spanish - Programming forum post about Pascal (forum, Q&A content)
12. `archive.softwareheritage.org` - English - Software archive file browser (code hosting, minimal content)
13. `archives.gentoo.org` - English - Gentoo mailing list patches (**high quality** technical discussion)
14. `atris.fz-juelich.de` - English - Scientific data file browser (repository, minimal content)
15. `blog.0x32.co.uk` - English - Technical blog about clipboard history (**high quality** blog post)
16. `blog.republicofdata.io` - English - Blog about AI agents and data scraping (**high quality** technical blog)
17. `camilord.com` - English - Personal coding blog (**high quality** technical content)
18. `cdnimg.ghbook.ir` - Arabic/Persian - Islamic digital library book page (religious text, mixed quality)
19. `chords.lacuerda.net` - Spanish/English - Guitar chords page (music, structured data)
20. `chromeos.guide` - English - ChromeOS device documentation (technical docs, verbose)
21. `code.pin13.net` - English - Git repository file browser (code hosting, minimal content)
22. `codepal.ai` - English - AI code generator output for C (generated content, mixed quality)
23. `codepal.ai` - English - AI code generator for R statistics (generated content, mixed quality)
24. `coratmosphere.fr` - French - Blog about writing complaint letters (**high quality** how-to article)
25. `czyt.tech` - Chinese/English - Arch Linux software guide (**high quality** technical tutorial)

First "high-quality" example: Record #2 (LinuxFocus article about BORG graphics) - a proper tutorial article with educational content. However, the first truly clean, well-structured technical content appears around records #6, #15-17, and #24-25.

## Problem (extract_text): 3 points

**(a)** Write a function that extracts text from a byte string containing raw HTML. Use `resiliparse.extract.html2text.extract_plain_text` to perform the extraction. This function needs a string, so you will need to first decode the byte string into a Unicode string. Be aware that the input byte string might not be encoded in UTF-8, so your function should be able to detect the encoding in case UTF-8 fails. Resiliparse also offers `resiliparse.parse.encoding.detect_encoding()`, which might be useful.

**Deliverable:** A function that takes a byte string containing HTML and returns a string containing the extracted text. Implement the adapter `[run_extract_text_from_html_bytes]` and make sure it passes `uv run pytest -k test_extract_text_from_html_bytes`

**(b)** Run your text extraction function on a single WARC file. Compare its output to the extracted text in the corresponding WET file. What differences and/or similarities do you notice? Which extraction seems better?

**Deliverable:** 2-3 sentence response comparing and contrasting the text extracted by your own function versus the extracted text in the WET files.

**Answer:** Both methods extract similar main content, but WET files include page titles at the beginning (e.g., "La Plenitud del obrar Cristiano | Librería Matrimonio") while our resiliparse extraction preserves more structural formatting like bullet points for navigation menus (e.g., `• Instagram`, `• Facebook`). WET extraction tends to produce cleaner, flattened text by omitting social media icons and navigation clutter. Overall, WET appears slightly better for training data as it provides cleaner prose-like output, though our extraction retains more of the original page structure.

## Problem (language_identification): 6 points

**(a)** Write a function that will take a Unicode string and identify the main language that is present in this string. Your function should return a pair, containing an identifier of the language and a score between 0 and 1 representing its confidence in that prediction.

**Deliverable:** A function that performs language identification, giving its top language prediction and a score. Implement the adapter `[run_identify_language]` and make sure it passes both tests in `uv run pytest -k test_identify_language`. Note that these tests assume a particular string identifier for English ("en") and Chinese ("zh"), so your test adapter should perform any applicable re-mapping, if necessary.

**(b)** The behavior of language models at inference time largely depends on the data they were trained on. As a result, issues in the data filtering pipeline can result in problems downstream. What issues do you think could arise from problems in the language identification procedure? In a higher-stakes scenario (such as when deploying a user-facing product), how would you go about mitigating these issues?

**Deliverable:** A 2-5 sentence response.

**Answer:** Misclassified languages can lead to training data contamination—e.g., non-English text in an "English-only" corpus may cause the model to generate mixed-language outputs or struggle with monolingual tasks. Low-resource languages may be systematically misclassified as higher-resource ones (e.g., Catalan as Spanish), causing underrepresentation and poor performance for minority language users. In higher-stakes deployments, mitigations include using ensemble classifiers, setting conservative confidence thresholds, implementing human-in-the-loop verification for edge cases, and maintaining language-specific evaluation sets to monitor downstream model performance across languages.

**(c)** Run your language identification system on text extracted from the WARC files (via your previously-implemented text extraction function). Manually identify the language in 20 random examples and compare your labels with the classifier predictions. Report any classifier errors. What fraction of documents are English? Based on your observations, what would be a suitable classifier confidence threshold to use in filtering?

**Deliverable:** A 2-5 sentence response.

**Answer:** Of 26,671 documents in the WARC file, 43.2% (11,521) were classified as English. In my manual review of 20 random samples, all classifier predictions were correct—languages included English, Russian, German, French, Spanish, Chinese, and Romanian. However, confidence scores varied widely: navigation-heavy or boilerplate-heavy pages (e.g., GitLab at 0.495, NFL Fantasy at 0.285) had low scores despite correct predictions, while content-rich pages typically scored above 0.9. A confidence threshold of 0.5-0.6 would be suitable for filtering, as it retains most correctly-classified documents while excluding uncertain predictions that often correspond to low-quality boilerplate content.

## Problem (mask_pii): 3 points

**(a)** Write a function to mask out emails. Your function will take a string as input, and replace all instances of email addresses with the string "|||EMAIL_ADDRESS|||". To detect email addresses, you can look up regular expressions that do this reliably.

**Deliverable:** A function that replaces all email addresses in a given string with the string "|||EMAIL_ADDRESS|||", returning a pair containing both the new string and the number of instances that were masked. Implement the adapter `[run_mask_emails]` and make sure it passes all tests in `uv run pytest -k test_mask_emails`.

**(b)** Write a function to mask out phone numbers. Your function will take a string as input, and replace all instances of phone numbers with the string "|||PHONE_NUMBER|||". Doing this reliably can be extremely challenging, as phone numbers might be written in an extremely diverse set of formats, but you should try to capture at least the most common phone number formats used in the United States, and be robust to minor syntactic deviations.

**Deliverable:** A function that replaces phone numbers in a given string with the string "|||PHONE_NUMBER|||", returning a pair containing both the new string and the number of instances that were masked. Implement the adapter `[run_mask_phone_numbers]` and make sure it passes `uv run pytest -k test_mask_phones`.

**(c)** Write a function to mask out IP addresses. For this problem, it is enough to focus on IPv4 addresses (4 numbers up to 255 separated by points). Your function will take a string as input, and replace all instances of IP addresses with the string "|||IP_ADDRESS|||".

**Deliverable:** A function that replaces IPv4 addresses in a given string with the string "|||IP_ADDRESS|||", returning a pair containing both the new string and the number of instances that were masked. Implement the adapter `[run_mask_ips]` and make sure it passes `uv run pytest -k test_mask_ips`.

**(d)** What problems do you think might arise downstream in a language model when these filters are naïvely applied on the training set? How might you mitigate these issues?

**Deliverable:** A 2-5 sentence response.

**Answer:** Naïve PII masking can cause several problems: (1) false positives may mask legitimate content like version numbers (e.g., "Python 3.10.0.1" matched as IP), mathematical expressions, or product codes, degrading the model's ability to handle technical content; (2) the model may learn to generate "|||EMAIL_ADDRESS|||" tokens in inappropriate contexts; (3) inconsistent masking across documents creates noise in the training signal. To mitigate these issues, one could use context-aware masking that considers surrounding text, replace PII with realistic synthetic data instead of placeholder tokens, or train the model to recognize and appropriately handle PII rather than simply removing it.

**(e)** Run your PII masking functions on text extracted from the WARC files (via your previously-implemented text extraction function). Look through 20 random examples where a replacement was made; give some examples of false positives and false negatives.

**Deliverable:** A 2-5 sentence response.

**Answer:** Out of 26,671 documents, 7,514 contained detected emails, 7,126 contained detected phone numbers, and 214 contained detected IPs. **False positives observed:** (1) Phone regex matched Facebook group IDs like `21361278617`, (2) Italian tax/company IDs like `11630700018` (C.F./P.IVA numbers) were incorrectly flagged as phone numbers, (3) Version/section numbers like `3.2.1.4` were matched as IP addresses. **False negatives likely include:** international phone formats (e.g., `+49 123 456 7890`), emails with newer TLDs (e.g., `.museum`, `.photography`), and phone numbers with country codes or extensions. The phone number regex is particularly prone to false positives since many numeric sequences happen to match the 10-digit pattern.

## Problem (harmful_content): 6 points

**(a)** Write a function to detect NSFW content.

**Deliverable:** A function that labels a given string as containing NSFW content or not, returning a pair containing both the label and a confidence score. Implement the adapter `[run_classify_nsfw]` and make sure it passes `uv run pytest -k test_classify_nsfw`. Note that this test is just a sanity check, taken from the Jigsaw dataset, but by no means asserts that your classifier is accurate, which you should validate.

**(b)** Write a function to detect toxic speech.

**Deliverable:** A function that labels a given string as consisting of toxic speech or not, returning a pair containing both the label and a confidence score. Implement the adapter `[run_classify_toxic_speech]` and make sure it passes `uv run pytest -k test_classify_toxic_speech`. Again, this test is just a sanity check, also taken from Jigsaw.

**(c)** What problems do you think might arise downstream in a language model when these filters are applied to create the training set? How might you mitigate these issues?

**Deliverable:** A 2-5 sentence response.

**Answer:** Aggressive harmful content filtering can systematically remove legitimate content, leading to several downstream issues: (1) non-English languages may be disproportionately filtered due to classifier bias toward English training data, reducing multilingual capabilities; (2) discussions about sensitive topics (e.g., sexual health education, hate speech research, legal cases involving violence) may be removed, limiting the model's ability to handle these topics appropriately; (3) over-filtering can create "holes" in the model's knowledge. Mitigations include using language-specific classifiers, setting conservative thresholds with human review for borderline cases, maintaining separate classifiers for different content types, and ensuring diverse annotator pools during classifier training.

**(d)** Run your harmful content filters on text extracted from the WARC files (via your previously-implemented text extraction function). Look through 20 random examples and compare the classifier predictions to your own judgments. Report any classifier errors. What fraction of documents are harmful? Based on your observations, what would be suitable classifier confidence threshold(s) to use in filtering?

**Deliverable:** A 2-5 sentence response.

**Answer:** Of 11,390 documents, 0.1% were classified as NSFW and 0.5% as toxic (0.5% total harmful). In my review of 20 harmful-classified examples, I found a ~57% false positive rate among high-confidence toxic predictions: legitimate sites like `eggplant-egg.com` (Japanese vintage store, score=0.991), `kmz-sbk.de` (German education center, score=0.973), and `www.q8car.com` (Kuwaiti car marketplace, NSFW score=0.88) were incorrectly flagged, while true positives included `teen-gay-boys.com`, `porntv.top`, and `xxxdownload.buzz`. The classifiers exhibit strong non-English bias—German, Russian, Arabic, and Japanese content frequently triggers false positives. A threshold of **0.95+ for NSFW** and **0.99+ for toxic** would be more appropriate, combined with language filtering to only apply these English-trained classifiers to English documents.

## Problem (gopher_quality_filters): 3 points

**(a)** Implement (at least) the subset of the Gopher quality filters as described above. For tokenizing text into words, you might find the NLTK package useful (specifically nltk.word_tokenize), though you're not required to use it.

**Deliverable:** A function that takes a string as its only argument and returns a boolean indicating whether the text passes the Gopher quality filters. Implement the adapter `[run_gopher_quality_filter]`. Then, make sure your filters pass the tests in `uv run pytest -k test_gopher`.

**(b)** Run your rule-based quality filter on text extracted from the WARC files (via your previously-implemented text extraction function). Look through 20 random examples and compare the filter predictions to your own judgment. Comment on any cases where the quality filters differ from your judgments.

**Deliverable:** A 2-5 sentence response.

**Answer:** Of 11,390 documents, 53.6% passed the Gopher quality filters and 46.4% failed. In my review of 20 random examples, most filter decisions were reasonable: documents failed primarily due to low alphabetic word ratio (<80%) caused by excessive product codes, prices, and phone numbers (e.g., `bagleyliquor.com` at 65.3%, `myapo-shop.de` at 59.0%), or too few words (<50) for short navigation-heavy pages. However, I disagree with some rejections: `leewasson.com` (French jewelry site) was rejected at 79.9% alphabetic ratio—just barely below the 80% threshold—despite containing reasonable prose, and Chinese/Japanese sites like `m.0591dxb.com` were rejected for mean word length >10 because CJK text tokenization by whitespace produces long "words." The filters work well for English content but are overly aggressive on non-English text and e-commerce pages with many numeric values.

## Problem (quality_classifier): 15 points

**(a)** Train a quality classifier that, given text, returns a numeric quality score.

**Deliverable:** A quality classifier for use in the next subproblem.

**(b)** Write a function that labels a page as high or low-quality, and provides a confidence score in the label.

**Deliverable:** A function taking a string as its only argument, and returning a pair with a label (high-quality or not) and a confidence score. Implement the adapter `[run_classify_quality]`. As a sanity check, make sure it correctly classifies the two examples we provide by running `uv run pytest -k test_classify_quality`.