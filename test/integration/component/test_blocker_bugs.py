# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
# 
#   http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
""" Tests for Blocker bugs
"""
import marvin
from nose.plugins.attrib import attr
from marvin.integration.lib.base import *
from marvin.integration.lib.utils import *
from marvin.integration.lib.common import *

#Import Local Modules
from marvin.cloudstackTestCase import *
from marvin.cloudstackAPI import *


class Services:
    """Test Services
    """

    def __init__(self):
        self.services = {
                         "domain": {
                                   "name": "Domain",
                        },
                        "account": {
                                    "email": "test@test.com",
                                    "firstname": "Test",
                                    "lastname": "User",
                                    "username": "test",
                                    # Random characters are appended for unique
                                    # username
                                    "password": "password",
                         },
                         "service_offering": {
                                    "name": "Tiny Instance",
                                    "displaytext": "Tiny Instance",
                                    "cpunumber": 1,
                                    "cpuspeed": 100,    # in MHz
                                    "memory": 128,       # In MBs
                        },
                        "disk_offering": {
                                    "displaytext": "Small",
                                    "name": "Small",
                                    "disksize": 1
                        },
                        "virtual_machine": {
                                    "displayname": "Test VM",
                                    "username": "root",
                                    "password": "password",
                                    "ssh_port": 22,
                                    "hypervisor": 'XenServer',
                                    "privateport": 22,
                                    "publicport": 22,
                                    "protocol": 'TCP',
                        },
                        "templates": {
                                    "displaytext": 'Template from snapshot',
                                    "name": 'Template from snapshot',
                                    "ostype": 'CentOS 5.3 (64-bit)',
                                    "templatefilter": 'self',
                                    "url": "http://download.cloud.com/releases/2.0.0/UbuntuServer-10-04-64bit.vhd.bz2",
                                    "hypervisor": 'XenServer',
                                    "format": 'VHD',
                                    "isfeatured": True,
                                    "ispublic": True,
                                    "isextractable": True,
                                    "passwordenabled": True,
                        },
                        "firewall_rule": {
                                    "cidrlist" : "0.0.0.0/0",
                                    "startport": 22,
                                    "endport": 22,
                                    "protocol": "TCP"
                        },
                        "ostype": 'CentOS 5.3 (64-bit)',
                        # Cent OS 5.3 (64 bit)
                        "sleep": 60,
                     }


class TestTemplate(cloudstackTestCase):

    def setUp(self):

        self.apiclient = self.testClient.getApiClient()
        self.dbclient = self.testClient.getDbConnection()
        self.cleanup = []
        return

    def tearDown(self):
        try:
            cleanup_resources(self.apiclient, self.cleanup)
        except Exception as e:
            raise Exception("Warning: Exception during cleanup : %s" % e)
        return

    @classmethod
    def setUpClass(cls):
        cls.services = Services().services
        cls.api_client = super(TestTemplate, cls).getClsTestClient().getApiClient()

        # Get Zone, Domain and templates
        cls.domain = get_domain(cls.api_client, cls.services)
        cls.zone = get_zone(cls.api_client, cls.services)
        cls.services['mode'] = cls.zone.networktype
        cls.services["virtual_machine"]["zoneid"] = cls.zone.id
        cls.services["templates"]["zoneid"] = cls.zone.id

        cls.service_offering = ServiceOffering.create(
                                            cls.api_client,
                                            cls.services["service_offering"]
                                            )
        cls.account = Account.create(
                            cls.api_client,
                            cls.services["account"],
                            domainid=cls.domain.id
                            )
        cls.services["account"] = cls.account.name

        cls._cleanup = [
                        cls.account,
                        cls.service_offering
                        ]
        return

    @classmethod
    def tearDownClass(cls):
        try:
            cls.api_client = super(TestTemplate, cls).getClsTestClient().getApiClient()
            #Cleanup resources used
            cleanup_resources(cls.api_client, cls._cleanup)

        except Exception as e:
            raise Exception("Warning: Exception during cleanup : %s" % e)

        return

    @attr(tags = ["advanced", "advancedns", "basic", "sg"])
    def test_01_create_template(self):
        """TS_BUG_002-Test to create and deploy VM using password enabled template
        """


        # Validate the following:
        #1. Create a password enabled template
        #2. Deploy VM using this template
        #3. Deploy VM should return password set in template.

        self.debug("Registering a new template")
        # Register new template
        template = Template.register(
                                    self.apiclient,
                                    self.services["templates"],
                                    zoneid=self.zone.id,
                                    account=self.account.name,
                                    domainid=self.account.domainid
                                    )
        self.debug("Registering template with ID: %s" % template.id)
        try:
            # Wait for template to download
            template.download(self.apiclient)
        except Exception as e:
            self.fail("Exception while downloading template %s: %s"\
                      % (template.id, e))

        self.cleanup.append(template)

        # Wait for template status to be changed across
        time.sleep(self.services["sleep"])

        list_template_response = Template.list(
                                            self.apiclient,
                                            templatefilter=\
                                            self.services["templates"]["templatefilter"],
                                            id=template.id,
                                            zoneid=self.zone.id
                                            )

        self.assertEqual(
                            isinstance(list_template_response, list),
                            True,
                            "Check list response returns a valid list"
                        )
        #Verify template response to check whether template added successfully
        self.assertNotEqual(
                            len(list_template_response),
                            0,
                            "Check template available in List Templates"
                        )
        template_response = list_template_response[0]

        self.assertEqual(
                            template_response.isready,
                            True,
                            "Check display text of newly created template"
                        )

        # Deploy new virtual machine using template
        virtual_machine = VirtualMachine.create(
                                 self.apiclient,
                                 self.services["virtual_machine"],
                                 templateid=template.id,
                                 accountid=self.account.name,
                                 domainid=self.account.domainid,
                                 serviceofferingid=self.service_offering.id,
                                 )
        self.debug("Deployed VM with ID: %s " % virtual_machine.id)
        self.assertEqual(
                         hasattr(virtual_machine, "password"),
                         True,
                         "Check if the deployed VM returned a password"
                        )
        return


class TestNATRules(cloudstackTestCase):

    @classmethod
    def setUpClass(cls):

        cls.api_client = super(TestNATRules, cls).getClsTestClient().getApiClient()
        cls.services = Services().services

        # Get Zone, Domain and templates
        cls.domain = get_domain(cls.api_client, cls.services)
        cls.zone = get_zone(cls.api_client, cls.services)
        cls.services['mode'] = cls.zone.networktype
        template = get_template(
                            cls.api_client,
                            cls.zone.id,
                            cls.services["ostype"]
                            )
        #Create an account, network, VM and IP addresses
        cls.account = Account.create(
                                cls.api_client,
                                cls.services["account"],
                                admin=True,
                                domainid=cls.domain.id
                                )
        cls.services["virtual_machine"]["zoneid"] = cls.zone.id
        cls.service_offering = ServiceOffering.create(
                                cls.api_client,
                                cls.services["service_offering"]
                                )
        cls.virtual_machine = VirtualMachine.create(
                                    cls.api_client,
                                    cls.services["virtual_machine"],
                                    templateid=template.id,
                                    accountid=cls.account.name,
                                    domainid=cls.account.domainid,
                                    serviceofferingid=cls.service_offering.id
                                )
        cls.public_ip = PublicIPAddress.create(
                                    cls.api_client,
                                    accountid=cls.account.name,
                                    zoneid=cls.zone.id,
                                    domainid=cls.account.domainid,
                                    services=cls.services["virtual_machine"]
                                    )
        cls._cleanup = [
                        cls.virtual_machine,
                        cls.account,
                        cls.service_offering
                        ]

    def setUp(self):
        self.apiclient = self.testClient.getApiClient()
        self.dbclient = self.testClient.getDbConnection()
        self.cleanup = []
        return

    def tearDown(self):
        try:
            cleanup_resources(self.apiclient, self.cleanup)
        except Exception as e:
            raise Exception("Warning: Exception during cleanup : %s" % e)
        return

    @classmethod
    def tearDownClass(cls):
        try:
            cls.api_client = super(TestNATRules, cls).getClsTestClient().getApiClient()
            cleanup_resources(cls.api_client, cls._cleanup)
        except Exception as e:
            raise Exception("Warning: Exception during cleanup : %s" % e)

    @attr(tags = ["advanced"])
    def test_01_firewall_rules_port_fw(self):
        """"Checking firewall rules deletion after static NAT disable"""


        # Validate the following:
        #1. Enable static NAT for a VM
        #2. Open up some ports. At this point there will be new rows in the
        #   firewall_rules table.
        #3. Disable static NAT for the VM.
        #4. Check fire wall rules are deleted from firewall_rules table.

        public_ip = self.public_ip.ipaddress

        # Enable Static NAT for VM
        StaticNATRule.enable(
                             self.apiclient,
                             public_ip.id,
                             self.virtual_machine.id
                            )
        self.debug("Enabled static NAT for public IP ID: %s" %
                                                    public_ip.id)

        #Create Static NAT rule, in fact it's firewall rule
        nat_rule = StaticNATRule.create(
                        self.apiclient,
                        self.services["firewall_rule"],
                        public_ip.id
                        )
        self.debug("Created Static NAT rule for public IP ID: %s" %
                                                    public_ip.id)
        self.debug("Checking IP address")
        ip_response = PublicIPAddress.list(
                                         self.apiclient,
                                         id = public_ip.id
                                        )
        self.assertEqual(
                            isinstance(ip_response, list),
                            True,
                            "Check ip response returns a valid list"
                        )
        self.assertNotEqual(
                            len(ip_response),
                            0,
                            "Check static NAT Rule is created"
                            )
        self.assertTrue(
                            ip_response[0].isstaticnat,
                            "IP is not static nat enabled"
                        )
        self.assertEqual(
                            ip_response[0].virtualmachineid,
                            self.virtual_machine.id,
                            "IP is not binding with the VM"
                        )

        self.debug("Checking Firewall rule")
        firewall_response = FireWallRule.list(
                                                self.apiclient,
                                                ipaddressid = public_ip.id,
                                                listall = True
                                             )
        self.assertEqual(
                            isinstance(firewall_response, list),
                            True,
                            "Check firewall response returns a valid list"
                        )
        self.assertNotEqual(
                            len(firewall_response),
                            0,
                            "Check firewall rule is created"
                            )
        self.assertEqual(
                            firewall_response[0].state,
                            "Active",
                            "Firewall rule is not active"
                        )
        self.assertEqual(
                            firewall_response[0].ipaddressid,
                            public_ip.id,
                            "Firewall rule is not static nat related"
                        )
        self.assertEqual(
                            firewall_response[0].startport,
                            str(self.services["firewall_rule"]["startport"]),
                            "Firewall rule is not with specific port"
                        )

        self.debug("Removed the firewall rule")
        nat_rule.delete(self.apiclient)

        self.debug("Checking IP address, it should still existed")
        ip_response = PublicIPAddress.list(
                                         self.apiclient,
                                         id = public_ip.id
                                        )
        self.assertEqual(
                            isinstance(ip_response, list),
                            True,
                            "Check ip response returns a valid list"
                        )
        self.assertNotEqual(
                            len(ip_response),
                            0,
                            "Check static NAT Rule is created"
                            )
        self.assertTrue(
                            ip_response[0].isstaticnat,
                            "IP is not static nat enabled"
                        )
        self.assertEqual(
                            ip_response[0].virtualmachineid,
                            self.virtual_machine.id,
                            "IP is not binding with the VM"
                        )

        self.debug("Checking Firewall rule, it should be removed")
        firewall_response = FireWallRule.list(
                                                self.apiclient,
                                                ipaddressid = public_ip.id,
                                                listall = True
                                             )
        self.assertEqual(
                            isinstance(firewall_response, list),
                            True,
                            "Check firewall response returns a valid list"
                        )
        if len(firewall_response) != 0 :
            self.assertEqual(
                            firewall_response[0].state,
                            "Deleting",
                            "Firewall rule should be deleted or in deleting state"
                        )
        return


class TestRouters(cloudstackTestCase):

    @classmethod
    def setUpClass(cls):
        cls.api_client = super(TestRouters, cls).getClsTestClient().getApiClient()
        cls.services = Services().services
        # Get Zone, Domain and templates
        cls.zone = get_zone(cls.api_client, cls.services)
        cls.services['mode'] = cls.zone.networktype
        cls.template = get_template(
                            cls.api_client,
                            cls.zone.id,
                            cls.services["ostype"]
                            )

        # Create an account, domain etc
        cls.domain = Domain.create(
                                   cls.api_client,
                                   cls.services["domain"],
                                   )
        cls.admin_account = Account.create(
                            cls.api_client,
                            cls.services["account"],
                            admin=True,
                            domainid=cls.domain.id
                            )

        cls.user_account = Account.create(
                            cls.api_client,
                            cls.services["account"],
                            domainid=cls.domain.id
                            )

        cls.services["virtual_machine"]["zoneid"] = cls.zone.id
        cls.services["virtual_machine"]["template"] = cls.template.id

        cls.service_offering = ServiceOffering.create(
                                            cls.api_client,
                                            cls.services["service_offering"]
                                            )

        cls._cleanup = [
                        cls.service_offering,
                        cls.admin_account,
                        cls.user_account,
                        cls.domain
                        ]
        return

    @classmethod
    def tearDownClass(cls):
        try:
            #Cleanup resources used
            cleanup_resources(cls.api_client, cls._cleanup)
        except Exception as e:
            raise Exception("Warning: Exception during cleanup : %s" % e)
        return

    def setUp(self):
        self.apiclient = self.testClient.getApiClient()
        self.dbclient = self.testClient.getDbConnection()
        self.cleanup = []
        return

    def tearDown(self):
        try:
            cleanup_resources(self.apiclient, self.cleanup)
        except Exception as e:
            raise Exception("Warning: Exception during cleanup : %s" % e)
        return

    @attr(tags = ["advanced", "advancedns"])
    def test_01_list_routers_admin(self):
        """TS_BUG_007-Check listRouters() using Admin User
        """


        # Validate the following
        # 1. PreReq: have rounters that are owned by other account
        # 2. Create domain and create accounts in that domain
        # 3. Create one VM for each account
        # 4. Using Admin , run listRouters. It should return all the routers

        vm_1 = VirtualMachine.create(
                                  self.apiclient,
                                  self.services["virtual_machine"],
                                  accountid=self.admin_account.name,
                                  domainid=self.admin_account.domainid,
                                  serviceofferingid=self.service_offering.id
                                  )
        self.debug("Deployed VM with ID: %s" % vm_1.id)
        vm_2 = VirtualMachine.create(
                                  self.apiclient,
                                  self.services["virtual_machine"],
                                  accountid=self.user_account.name,
                                  domainid=self.user_account.domainid,
                                  serviceofferingid=self.service_offering.id
                                  )
        self.debug("Deployed VM with ID: %s" % vm_2.id)
        routers = list_routers(
                               self.apiclient,
                               account=self.admin_account.name,
                               domainid=self.admin_account.domainid,
                               )
        self.assertEqual(
                            isinstance(routers, list),
                            True,
                            "Check list response returns a valid list"
                        )
        # ListRouter Should return 2 records
        self.assertEqual(
                             len(routers),
                             1,
                             "Check list router response"
                             )
        for router in routers:
            self.assertEqual(
                        router.state,
                        'Running',
                        "Check list router response for router state"
                    )
        return


class TestRouterRestart(cloudstackTestCase):

    @classmethod
    def setUpClass(cls):

        cls.api_client = super(TestRouterRestart, cls).getClsTestClient().getApiClient()
        cls.services = Services().services
        # Get Zone, Domain and templates
        cls.domain = get_domain(cls.api_client, cls.services)
        cls.zone = get_zone(cls.api_client, cls.services)
        cls.services['mode'] = cls.zone.networktype
        template = get_template(
                            cls.api_client,
                            cls.zone.id,
                            cls.services["ostype"]
                            )
        cls.services["virtual_machine"]["zoneid"] = cls.zone.id

        #Create an account, network, VM and IP addresses
        cls.account = Account.create(
                                     cls.api_client,
                                     cls.services["account"],
                                     domainid=cls.domain.id
                                     )
        cls.service_offering = ServiceOffering.create(
                                            cls.api_client,
                                            cls.services["service_offering"]
                                            )
        cls.vm_1 = VirtualMachine.create(
                                    cls.api_client,
                                    cls.services["virtual_machine"],
                                    templateid=template.id,
                                    accountid=cls.account.name,
                                    domainid=cls.account.domainid,
                                    serviceofferingid=cls.service_offering.id
                                    )
        cls.cleanup = [
                       cls.vm_1,
                       cls.account,
                       cls.service_offering
                       ]
        return

    @classmethod
    def tearDownClass(cls):
        try:
            cls.api_client = super(TestRouterRestart, cls).getClsTestClient().getApiClient()
            #Clean up, terminate the created templates
            cleanup_resources(cls.api_client, cls.cleanup)

        except Exception as e:
            raise Exception("Warning: Exception during cleanup : %s" % e)
        return

    def setUp(self):
        self.apiclient = self.testClient.getApiClient()
        return

    def tearDown(self):
        # No need
        return

    @attr(tags = ["advanced", "basic", "sg", "advancedns", "eip"])
    def test_01_restart_network_cleanup(self):
        """TS_BUG_008-Test restart network
        """


        # Validate the following
        # 1. When cleanup = true, router is destroyed and a new one created
        # 2. New router will have new publicIp and linkLocalIp and
        #    all it's services should resume

        # Find router associated with user account
        list_router_response = list_routers(
                                    self.apiclient,
                                    account=self.account.name,
                                    domainid=self.account.domainid
                                    )
        self.assertEqual(
                            isinstance(list_router_response, list),
                            True,
                            "Check list response returns a valid list"
                        )
        router = list_router_response[0]

        #Store old values before restart
        old_linklocalip = router.linklocalip

        timeout = 10
        # Network should be in Implemented or Setup stage before restart
        while True:
            networks = Network.list(
                                 self.apiclient,
                                 account=self.account.name,
                                 domainid=self.account.domainid
                                 )
            network = networks[0]
            if network.state in ["Implemented", "Setup"]:
                break
            elif timeout == 0:
                break
            else:
                time.sleep(60)
                timeout = timeout - 1

        self.debug("Restarting network: %s" % network.id)
        cmd = restartNetwork.restartNetworkCmd()
        cmd.id = network.id
        cmd.cleanup = True
        self.apiclient.restartNetwork(cmd)

        # Get router details after restart
        list_router_response = list_routers(
                                    self.apiclient,
                                    account=self.account.name,
                                    domainid=self.account.domainid
                                    )
        self.assertEqual(
                            isinstance(list_router_response, list),
                            True,
                            "Check list response returns a valid list"
                        )
        router = list_router_response[0]

        self.assertNotEqual(
                            router.linklocalip,
                            old_linklocalip,
                            "Check link-local IP after restart"
                        )
        return


class TestTemplates(cloudstackTestCase):

    @classmethod
    def setUpClass(cls):

        cls.services = Services().services
        cls.api_client = super(TestTemplates, cls).getClsTestClient().getApiClient()

        # Get Zone, templates etc
        cls.domain = get_domain(cls.api_client, cls.services)
        cls.zone = get_zone(cls.api_client, cls.services)
        cls.services['mode'] = cls.zone.networktype

        template = get_template(
                            cls.api_client,
                            cls.zone.id,
                            cls.services["ostype"]
                            )
        cls.services["virtual_machine"]["zoneid"] = cls.zone.id
        cls.account = Account.create(
                            cls.api_client,
                            cls.services["account"],
                            domainid=cls.domain.id
                            )

        cls.services["account"] = cls.account.name
        cls.service_offering = ServiceOffering.create(
                                            cls.api_client,
                                            cls.services["service_offering"],
                                        )

        # create virtual machine
        cls.virtual_machine = VirtualMachine.create(
                                    cls.api_client,
                                    cls.services["virtual_machine"],
                                    templateid=template.id,
                                    accountid=cls.account.name,
                                    domainid=cls.account.domainid,
                                    serviceofferingid=cls.service_offering.id,
                                    )
        #Stop virtual machine
        cls.virtual_machine.stop(cls.api_client)

        #Wait before server has be successfully stopped
        time.sleep(30)
        list_volume = Volume.list(
                                   cls.api_client,
                                   virtualmachineid=cls.virtual_machine.id,
                                   type='ROOT',
                                   listall=True
                                   )
        try:
            if isinstance(list_volume, list):
                cls.volume = list_volume[0]
        except Exception as e:
            raise Exception("Warning: Exception during setup : %s" % e)

        cls._cleanup = [
                        cls.service_offering,
                        cls.account,
                        ]

    @classmethod
    def tearDownClass(cls):
        try:
            cls.api_client = super(TestTemplates, cls).getClsTestClient().getApiClient()
            #Cleanup created resources such as templates and VMs
            cleanup_resources(cls.api_client, cls._cleanup)

        except Exception as e:
            raise Exception("Warning: Exception during cleanup : %s" % e)

        return

    def setUp(self):

        self.apiclient = self.testClient.getApiClient()
        self.dbclient = self.testClient.getDbConnection()
        self.cleanup = []
        return

    def tearDown(self):
        try:
            #Clean up, terminate the created templates
            cleanup_resources(self.apiclient, self.cleanup)

        except Exception as e:
            raise Exception("Warning: Exception during cleanup : %s" % e)

        return

    @attr(speed = "slow")
    @attr(tags = ["advanced", "advancedns", "basic", "sg", "eip"])
    def test_01_check_template_size(self):
        """TS_BUG_009-Test the size of template created from root disk
        """


        # Validate the following:
        # 1. Deploy new VM using the template created from Volume
        # 2. VM should be in Up and Running state

        #Create template from volume
        template = Template.create(
                                   self.apiclient,
                                   self.services["templates"],
                                   self.volume.id,
                                   account=self.account.name,
                                   domainid=self.account.domainid
                                )
        self.debug("Creating template with ID: %s" % template.id)
        # Volume and Template Size should be same
        self.assertEqual(
                             template.size,
                             self.volume.size,
                             "Check if size of template and volume are same"
                             )
        return

    @attr(speed = "slow")
    @attr(tags = ["advanced", "advancedns", "basic", "sg", "eip"])
    def test_02_check_size_snapshotTemplate(self):
        """TS_BUG_010-Test check size of snapshot and template
        """


        # Validate the following
        # 1. Deploy VM using default template, small service offering
        #    and small data disk offering.
        # 2. Perform snapshot on the root disk of this VM.
        # 3. Create a template from snapshot.
        # 4. Check the size of snapshot and template

        # Create a snapshot from the ROOTDISK
        snapshot = Snapshot.create(
                                   self.apiclient,
                                   self.volume.id,
                                   account=self.account.name,
                                   domainid=self.account.domainid
                                   )
        self.debug("Created snapshot with ID: %s" % snapshot.id)
        snapshots = Snapshot.list(
                                   self.apiclient,
                                   id=snapshot.id
                                   )
        self.assertEqual(
                            isinstance(snapshots, list),
                            True,
                            "Check list response returns a valid list"
                        )
        self.assertNotEqual(
                            snapshots,
                            None,
                            "Check if result exists in list snapshots call"
                            )
        self.assertEqual(
                            snapshots[0].id,
                            snapshot.id,
                            "Check snapshot id in list resources call"
                        )

        # Generate template from the snapshot
        template = Template.create_from_snapshot(
                                    self.apiclient,
                                    snapshot,
                                    self.services["templates"]
                                    )
        self.cleanup.append(template)

        self.debug("Created template from snapshot with ID: %s" % template.id)
        templates = Template.list(
                                self.apiclient,
                                templatefilter=\
                                self.services["templates"]["templatefilter"],
                                id=template.id
                                )
        self.assertEqual(
                            isinstance(templates, list),
                            True,
                            "Check list response returns a valid list"
                        )
        self.assertNotEqual(
                            templates,
                            None,
                            "Check if result exists in list item call"
                            )

        self.assertEqual(
                            templates[0].isready,
                            True,
                            "Check new template state in list templates call"
                        )
        # check size of template with that of snapshot
        self.assertEqual(
                            templates[0].size,
                            self.volume.size,
                            "Derived template size (%s) does not match snapshot size (%s)" % (templates[0].size, self.volume.size)
                        )
        return

    @attr(speed = "slow")
    @attr(tags = ["advanced", "advancedns", "basic", "sg", "eip"])
    def test_03_reuse_template_name(self):
        """TS_BUG_011-Test Reusing deleted template name
        """


        # Validate the following
        # 1. Deploy VM using default template, small service offering
        #    and small data disk offering.
        # 2. Perform snapshot on the root disk of this VM.
        # 3. Create a template from snapshot.
        # 4. Delete the template and create a new template with same name
        # 5. Template should be created succesfully

        # Create a snapshot from the ROOTDISK
        snapshot = Snapshot.create(
                                   self.apiclient,
                                   self.volume.id,
                                   account=self.account.name,
                                   domainid=self.account.domainid
                                   )
        self.debug("Created snapshot with ID: %s" % snapshot.id)
        snapshots = Snapshot.list(
                                   self.apiclient,
                                   id=snapshot.id
                                   )
        self.assertEqual(
                            isinstance(snapshots, list),
                            True,
                            "Check list response returns a valid list"
                        )
        self.assertNotEqual(
                            snapshots,
                            None,
                            "Check if result exists in list snapshots call"
                            )
        self.assertEqual(
                            snapshots[0].id,
                            snapshot.id,
                            "Check snapshot id in list resources call"
                        )

        # Generate template from the snapshot
        template = Template.create_from_snapshot(
                                    self.apiclient,
                                    snapshot,
                                    self.services["templates"],
                                    random_name=False
                                    )
        self.debug("Created template from snapshot: %s" % template.id)
        templates = Template.list(
                                self.apiclient,
                                templatefilter=\
                                self.services["templates"]["templatefilter"],
                                id=template.id
                                )
        self.assertEqual(
                            isinstance(templates, list),
                            True,
                            "Check list response returns a valid list"
                        )
        self.assertNotEqual(
                            templates,
                            None,
                            "Check if result exists in list item call"
                            )

        self.assertEqual(
                            templates[0].isready,
                            True,
                            "Check new template state in list templates call"
                        )

        self.debug("Deleting template: %s" % template.id)
        template.delete(self.apiclient)

        # Wait for some time to ensure template state is reflected in other calls
        time.sleep(self.services["sleep"])

        # Generate template from the snapshot
        self.debug("Creating template from snapshot: %s with same name" %
                                                                template.id)
        template = Template.create_from_snapshot(
                                    self.apiclient,
                                    snapshot,
                                    self.services["templates"],
                                    random_name=False
                                    )

        templates = Template.list(
                                self.apiclient,
                                templatefilter=\
                                self.services["templates"]["templatefilter"],
                                id=template.id
                                )
        self.assertEqual(
                            isinstance(templates, list),
                            True,
                            "Check list response returns a valid list"
                        )
        self.assertNotEqual(
                            templates,
                            None,
                            "Check if result exists in list item call"
                            )

        self.assertEqual(
                            templates[0].name,
                            self.services["templates"]["name"],
                            "Check the name of the template"
                        )
        return
