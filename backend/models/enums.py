import enum

class ProjectRole(int, enum.Enum):
    MANAGER = 1
    MEMBER = 2
    VIEWER = 3

    @classmethod
    def from_string(cls, role_str: str) -> "ProjectRole":
        role_map = {
            "manager": cls.MANAGER,
            "member": cls.MEMBER,
            "viewer": cls.VIEWER
        }
        return role_map.get(role_str.lower(), cls.MEMBER)

    def to_string(self) -> str:
        role_map = {
            self.MANAGER: "manager",
            self.MEMBER: "member",
            self.VIEWER: "viewer"
        }
        return role_map[self]

class ProjectStage(str, enum.Enum):
    TODO = "to_do"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled" 