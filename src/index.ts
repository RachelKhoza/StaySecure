import yargs from 'yargs';
import { hideBin } from 'yargs/helpers';
import { getUserInfo, getUserLanguages 
} from './githubClient';
import {
  addUser,
  addLanguage,
  getUsers,
  getUsersByLocation
} from './repository';


// Parse the cmd line arguments using yargs
const argv = yargs(hideBin(process.argv)) 
//define fetch cmd to fetch github user info
  .command('fetch [username]', 'Fetch GitHub user info', (yargs) => { 
    return yargs.positional('username', {
      describe: 'GitHub username',
      type: 'string',
      demandOption: true //make username required
    });
  }, async (argv) => {
    if (argv.username) {
      //fetch the info form github
      const userInfo = await getUserInfo(argv.username);
      await addUser(argv.username, userInfo.name, userInfo.location);
      const userLanguages = await getUserLanguages(argv.username);
      const users = await getUsers();
      const user = users.find((user) => user.username === argv.username);
      if (user) {
        for (const language of userLanguages) {
          await addLanguage(user.id, language);
        }
      }
    }
  })
  //define the list cmd to list our users
  .command('list', 'List all users', async () => {
    const users = await getUsers();
    console.log(users);
  })
  //this cmd will list users by location  
  .command('listByLocation [location]', 'List users by location', (yargs) => {
    return yargs.positional('location', {
      describe: 'Location',
      type: 'string',
      demandOption: true
    });
  }, async (argv) => {
    if (argv.location) {
      const users = await getUsersByLocation(argv.location);
      console.log(users);
    }
  })
  .help()
  .argv;


  Thanks for looping me in — I really appreciate the background and your perspective on the Northwave alerts. You make a solid point about improving visibility and accountability through ServiceNow.

Since I’ve just stepped in as DevSecOps, I’m still getting familiar with how the Cloud Ops and Infra workflows tie into alert handling. From what I’ve gathered so far, Cloud Ops is already quite stretched across infrastructure uptime, scaling, and incident response, and they haven’t had a dedicated security engineer in place before now.

Here’s what I’d suggest:
	•	For now: I can help get the Northwave alerts logged in ServiceNow so we at least start tracking them properly. That’ll give us a single source of truth and some history to work from.
	•	Next step: Once we’ve got visibility, we can agree on a split — Cloud Ops can stay focused on operational incidents, while I’ll start building out a security triage process for the alerts that need deeper follow-up.
	•	Down the line: We could look into automating the alert-to-ticket flow between Northwave and ServiceNow to cut down manual effort and response lag.

Maybe we can grab a quick call or chat to align on who handles what before involving Cloud Ops leadership. That way we can present a clean plan that works for everyone.