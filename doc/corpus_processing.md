# Processing scholar literature

Here is some documentation on the large scale processing of Open Access scholar articles by the [Softcite software mention recognizer](https://github.com/ourresearch/software-mentions), used as one channel to populate the Knowledge Base. We use Jetstream cloud environment part of XSEDE:

```
Stewart, C.A., Cockerill, T.M., Foster, I., Hancock, D., Merchant, N., Skidmore, E., Stanzione, D., Taylor, J., 
Tuecke, S., Turner, G., Vaughn, M., and Gaffney, N.I., Jetstream: a self-provisioned, scalable science and 
engineering cloud environment. 2015, In Proceedings of the 2015 XSEDE Conference: Scientific Advancements 
Enabled by Enhanced Cyberinfrastructure. St. Louis, Missouri.  ACM: 2792774.  p. 1-8. 
http://dx.doi.org/10.1145/2792745.2792774 
```

The starting point is the Unpaywall dataset dump. Used version is `unpaywall_snapshot_2021-07-02T151134.jsonl.gz`.  The full `jsonl` file is randomly sliced into 2000 partitions, containing only entries with an OA link. We used the "preferred" Unpaywall OA link, which prioritizes the Gold OA version (so for instance prioritizing the final published version over preprints). 

Each partition contains around 14K entries, for a total of approx. 28.3M entries have an OA link. The size of the partition is adapted to the total of 60GB of storage attached to each instance, considering around 15GB already used by the system and the Softcite docker image. 

A processing instance is prepared as an Ubuntu instance containing the following:

- base Ubuntu 18.04 Devel and Docker (~ 4.4 GB, very optimized for space) (https://use.jetstream-cloud.org/application/images/717)
- Docker image of the [Softcite software mention recognizer](https://github.com/ourresearch/software-mentions) https://hub.docker.com/r/grobid/software-mentions (`0.7.1-SNAPSHOT`) and [grobid](https://github.com/kermitt2/grobid) https://hub.docker.com/r/lfoppiano/grobid (`0.7.0`) 
- Install of [biblio-glutton-harvester](https://github.com/kermitt2/biblio-glutton-harvester)
- Install of the python client for the Softcite software mention recognizer: https://github.com/softcite/software_mentions_client

Around 40 instances based on this Ubuntu settings can be started at the same time on Jetstream. Deploying one image appears relatively time consuming, around ten minutes each. ssh keys are set at the Jetstream web interface and it will ensure that every instance is available over ssh without copying the public key on the instance. 

The process for each instance is then as follow:

- we upload one Unpaywall partition to the instance: 

```bash
scp /media/lopez/data2/biblio/unpaywall_partitions_2000/unpaywall_snapshot_2021-07-02T151134.jsonl_XXXX.jsonl.gz patricelopez@XXX.XXX.XX.XXX:/home/patricelopez/
```

- in the instance, we launch an harvesting process for this partition: 

```bash
cd biblio-glutton-harvester
python3 OAHarvester.py --unpaywall ../unpaywall_snapshot_2021-07-02T151134.jsonl_XXXX.jsonl.gz

```

- after a few hours, we launch a software mention recognition for this partition, using a config file for using the SciBERT-CRF model (we use only CPU):

```bash
cd software_mentions_client
python3 software_mention_client.py --data-path ../biblio-glutton-harvester/data
```

The results are produced as json file along with the PDFs (under `biblio-glutton-harvester/data`), in the harvested file hierarchy, we don't use a MongoDB storage at this point. Optionally we can run Grobid too on the PDF, to produce XML TEI representations that can be used for additional extractions (e.g. affiliations, funding or paper abstract).

After removing the PDF files to keep only the software extractions (and optionally the Grobid TEI XML), we centralize then the results in one machine (this machine having back-up!) with rsync to merge all the data directories:

```bash
find biblio-glutton-harvester/data -name *.pdf -delete
rsync -avh --progress biblio-glutton-harvester/data patricelopez@XXX.XXX.XX.XXX:/home/patricelopez/softcite_run/data
```

The centralized results can then be loaded in one step in MongoDB:

```bash
cd software_mentions_client
python3 software_mention_client.py --load --data_path /home/patricelopez/softcite_run/data
```

From the MongoDB data, we can then populate the Knowledge Base, see [Import software mentions](https://github.com/softcite/softcite_kb#import-software-mentions). 

As a complementary resource, we also use one existing home server with GPU (nvidia 1080Ti), processing PDF 10-12 times faster than one Jetstream CPU-only instance. This home instance works with 10 partitions on one time, having more storage space. This server alone has thus the capacity of around 12 Jetstream instances. 

Using SciBERT-CRF model, we can process in average 0.04 PDF per second on one mediuem Jetstream instance (6 cores, CPU), in comparison to 0.53 PDF per second on a workstation with GPU (nvidia 1080Ti, 8 cores CPU). In this setting, only the software mention recognition relies on GPU if available, all the other processing (like GROBID) use CPU.

The overall maximum resource is thus equivalent to 50 Jetstream instances, processing around 2.2 PDF per second with the SciBERT-CRF model. We are still at a total of around 2-3 months of processing for the whole Unpaywall collection, taking into account harvesting rate and PDF filtering. It is a slow process, but we are entirely at a zero cost mode, using only free available computing resources, while still processing a huge amount of PDF as compared to any similar academic projects involving mining of scholar documents. 
